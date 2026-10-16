r"""Graba la presentacion como video, cuadro por cuadro, con un reloj virtual.

Grabar la pantalla en tiempo real da saltos: cada captura tarda distinto y las
animaciones siguen corriendo mientras tanto. Aqui el tiempo NO corre solo:

  * un script inyectado reemplaza performance.now, Date.now, requestAnimationFrame,
    setTimeout y setInterval por un reloj que solo avanza cuando este programa lo
    pide (window.__avanzar(ms));
  * cada animacion y transicion CSS se pausa al nacer y se coloca a mano en su
    instante exacto (Web Animations API: currentTime);
  * entre cuadro y cuadro se avanza exactamente 1000/fps ms y se toma la captura.

Asi el video es identico en cada corrida y ninguna animacion se acelera ni se
atrasa, por lento que sea tomar la captura. La presentacion corre en su modo
?video, que avanza sola paso por paso.

Los cuadros se entregan como JPEG al ffmpeg que trae Playwright (tiene VP8/WebM).

    python LoL_PresentacionHistoria/scripts/video.py                # video completo
    python LoL_PresentacionHistoria/scripts/video.py --desde 6 --segundos 4 --prueba
"""
from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import os
import pathlib
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
DECK = BASE / "presentacion_historia.html"
SALIDA = BASE / "video"

RELOJ = r"""
(() => {
  let t = 0, sig = 1;
  const timers = new Map(), rafs = new Map();
  const t0Date = 1760000000000;
  performance.now = () => t;
  Date.now = () => t0Date + t;
  window.requestAnimationFrame = cb => { const id = sig++; rafs.set(id, cb); return id; };
  window.cancelAnimationFrame = id => rafs.delete(id);
  window.setTimeout = (cb, ms, ...a) => {
    const id = sig++; timers.set(id, { at: t + Math.max(0, +ms || 0), cb, a, cada: 0 }); return id; };
  window.setInterval = (cb, ms, ...a) => {
    const id = sig++; const c = Math.max(1, +ms || 0); timers.set(id, { at: t + c, cb, a, cada: c }); return id; };
  window.clearTimeout = window.clearInterval = id => timers.delete(id);

  // Una animacion pausada por la API queda «desligada» de su CSS: Chrome ya no la cancela
  // cuando el elemento cambia de clase. Sin esto, la animacion de ENTRADA de una lamina
  // seguia viva (con fill: both) despues de que la lamina pasaba a «sale», y pisaba el
  // recorte de salida: la lamina vieja se quedaba encimada bajo la nueva. Aqui se imita lo
  // que haria el navegador: se cancela la animacion cuyo nombre ya no esta en el CSS del
  // elemento (o cuyo elemento ya no se dibuja), y la transicion que ya termino.
  const vigente = an => {
    const fx = an.effect, el = fx && fx.target;
    if (!el || !el.isConnected) return false;
    if (typeof CSSAnimation !== "undefined" && an instanceof CSSAnimation) {
      const cs = getComputedStyle(el, fx.pseudoElement || null);
      if (cs.display === "none") return false;
      return cs.animationName.split(",").map(s => s.trim()).includes(an.animationName);
    }
    if (typeof CSSTransition !== "undefined" && an instanceof CSSTransition) {
      const tm = fx.getComputedTiming();
      return (an.currentTime || 0) < tm.endTime;
    }
    return true;
  };
  const sincroniza = () => {
    for (const an of document.getAnimations()) {
      if (an.__t0 === undefined) { an.__t0 = t; an.pause(); }
      else if (!vigente(an)) { an.cancel(); continue; }
      an.currentTime = Math.max(0, t - an.__t0);
    }
  };
  window.__avanzar = ms => {
    const fin = t + ms;
    for (;;) {                       // temporizadores vencidos, en orden
      let prox = null;
      for (const [id, x] of timers) if (x.at <= fin && (!prox || x.at < prox[1].at)) prox = [id, x];
      if (!prox) break;
      const [id, x] = prox;
      t = Math.max(t, x.at);
      if (x.cada) x.at += x.cada; else timers.delete(id);
      try { x.cb(...x.a); } catch (e) { console.error(e); }
      sincroniza();                  // lo que nacio con ese temporizador arranca en su instante
    }
    t = fin;
    const cola = [...rafs.values()]; rafs.clear();
    for (const cb of cola) { try { cb(t); } catch (e) { console.error(e); } }
    sincroniza();
    return t;
  };
  window.__reloj = () => t;
})();
"""


def ffmpeg(propio: str | None = None) -> str:
    """El ffmpeg indicado con --ffmpeg (o en la variable FFMPEG); si no, el de Playwright."""
    propio = propio or os.environ.get("FFMPEG")
    if propio:
        if not pathlib.Path(propio).is_file():
            raise SystemExit(f"no existe el ffmpeg indicado: {propio}")
        return propio
    cand = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\ffmpeg-*\ffmpeg-win64.exe")))
    if not cand:
        raise SystemExit("no encuentro el ffmpeg de Playwright (python -m playwright install ffmpeg)")
    return cand[-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--desde", type=int, default=1, help="lamina inicial (1 = portada)")
    ap.add_argument("--segundos", type=float, default=0, help="cortar a los N segundos (0 = hasta el final)")
    ap.add_argument("--prueba", action="store_true", help="no codifica: imprime huella de los cuadros")
    ap.add_argument("--salida", default=str(SALIDA / "historia.webm"))
    ap.add_argument("--muestras", type=float, default=0, help="guardar un cuadro cada N segundos en video/muestras/")
    ap.add_argument("--ffmpeg", help="ruta a un ffmpeg con H.264 (necesario para --salida *.mp4)")
    ap.add_argument("--ventana", type=int, default=0,
                    help="revisar la transicion hacia la lamina K: guarda TODOS los cuadros de 0.3 s antes "
                         "a 1.5 s despues en video/muestras/ y termina (no codifica)")
    a = ap.parse_args()
    if a.ventana:                      # empezar en la lamina anterior y no codificar
        a.desde, a.prueba = max(1, a.ventana - 1), True
    dir_m = SALIDA / "muestras"
    if a.muestras or a.ventana:
        dir_m.mkdir(parents=True, exist_ok=True)
        for f in [*dir_m.glob("*.jpg"), *dir_m.glob("*.png")]:
            f.unlink()

    paso = 1000 / a.fps
    url = DECK.as_uri() + f"?video#d{a.desde}"
    huella = hashlib.sha256()
    enc = None
    if not a.prueba:
        pathlib.Path(a.salida).parent.mkdir(exist_ok=True)
        if a.salida.lower().endswith(".mp4"):
            # H.264: lo abre cualquier reproductor, PowerPoint incluido. crf 16 ≈ sin perdida visible;
            # faststart pone el indice al inicio para que empiece a reproducirse de inmediato.
            # El JPEG llega en rango completo (yuvj420p); se convierte a rango estandar BT.709,
            # que es lo que esperan los reproductores (si no, algunos lo muestran lavado).
            codec = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                     # tune film + aq-mode 3 conservan el tramado de los fondos oscuros (si el
                     # codificador lo alisa, vuelven los anillos del degradado)
                     "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "film",
                     "-x264-params", "aq-mode=3:aq-strength=0.9",
                     "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "iec61966-2-1", "-movflags", "+faststart"]
        else:
            codec = ["-c:v", "libvpx", "-b:v", "12M", "-crf", "6", "-qmin", "0", "-qmax", "24",
                     "-deadline", "good", "-cpu-used", "1", "-auto-alt-ref", "0", "-pix_fmt", "yuv420p"]
        enc = subprocess.Popen(
            [ffmpeg(a.ffmpeg), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(a.fps),
             # «-» no funciona en el ffmpeg minimo de Playwright; el protocolo pipe:0 si
             "-c:v", "mjpeg", "-i", "pipe:0", *codec, a.salida],
            stdin=subprocess.PIPE)

    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        pag = nav.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        errores: list[str] = []
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.add_init_script(RELOJ)
        pag.goto(url)
        pag.evaluate("document.fonts.ready.then(() => Promise.all([...document.images].map(i => i.decode().catch(() => 0))))")
        cdp = pag.context.new_cdp_session(pag)
        n, t_ini = 0, time.time()
        limite = a.segundos * 1000 if a.segundos else float("inf")
        t_cambio = None
        while True:
            vt = pag.evaluate(f"__avanzar({paso})")
            if a.ventana:
                if t_cambio is None:
                    if pag.evaluate("location.hash") != f"#d{a.ventana}":
                        continue
                    t_cambio = vt
                if vt - t_cambio > 1500:
                    break
                img = base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png"})["data"])
                (dir_m / f"v{int(vt - t_cambio):05d}.png").write_bytes(img)
                n += 1
                continue
            img = base64.b64decode(cdp.send("Page.captureScreenshot",
                                            {"format": "jpeg", "quality": 97})["data"])
            huella.update(img)
            if enc:
                enc.stdin.write(img)
            if a.muestras and n % max(1, round(a.muestras * a.fps)) == 0:
                (dir_m / f"t{n / a.fps:07.2f}.jpg").write_bytes(img)
            n += 1
            if n % (a.fps * 10) == 0:
                print(f"  {n / a.fps:6.1f} s de video  ({time.time() - t_ini:5.0f} s reales)", flush=True)
            if vt >= limite or pag.evaluate("window.__fin === true"):
                break
        nav.close()
    if enc:
        enc.stdin.close()
        enc.wait()
    print(f"{n} cuadros = {n / a.fps:.1f} s · huella {huella.hexdigest()[:16]}")
    if errores:
        print("ERRORES:", *errores, sep="\n  ")
        return 1
    if enc:
        print("video:", a.salida, f"{pathlib.Path(a.salida).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

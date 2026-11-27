"""Inicialização: python servidor.py [--demo] [--host HOST] [--porta PORT]"""
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="inicia com banco de simulação")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--porta", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args()
    if args.demo:
        os.environ["MODO_DEMO"] = "1"
    import uvicorn
    if not args.sem_navegador:
        import threading, webbrowser
        threading.Timer(1, webbrowser.open, args=(f"http://127.0.0.1:{args.porta}",)).start()
    uvicorn.run("api:app", host=args.host, port=args.porta, reload=False, log_level="info")


if __name__ == "__main__":
    main()

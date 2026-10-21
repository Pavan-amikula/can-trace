import argparse
import json
from pathlib import Path

from .data import Encoder, Frame, load_frames
from .forensics import verify_case
from .live import StreamDetector
from .conditional import ConditionalMPS


def main():
    parser = argparse.ArgumentParser(
        description="CAN Trace: passive CAN anomaly analysis"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("evaluate")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8000)
    verify = sub.add_parser("verify")
    verify.add_argument("case")
    monitor = sub.add_parser(
        "monitor", help="passive receive only; never transmits frames"
    )
    monitor.add_argument("--interface", default="socketcan")
    monitor.add_argument("--channel", default="vcan0")
    monitor.add_argument("--model", default="artifacts/model.npz")
    replay = sub.add_parser("replay")
    replay.add_argument("capture")
    replay.add_argument("--model", default="artifacts/model.npz")
    args = parser.parse_args()
    if args.command == "evaluate":
        from .evaluate import run

        run()
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("cantrace.api:app", host="127.0.0.1", port=args.port)
    elif args.command == "verify":
        valid = verify_case(json.loads(Path(args.case).read_text()))
        print("Integrity checks passed" if valid else "INTEGRITY FAILURE")
        raise SystemExit(0 if valid else 1)
    else:
        model, meta = ConditionalMPS.load(args.model)
        detector = StreamDetector(model, Encoder.restore(meta))
        if args.command == "replay":
            for frame in load_frames(args.capture):
                result = detector.feed(frame)
                if result and result["alert"]:
                    print(json.dumps(result))
        else:
            import can

            with can.Bus(
                interface=args.interface,
                channel=args.channel,
                receive_own_messages=False,
            ) as bus:
                try:
                    while True:
                        msg = bus.recv(timeout=1)
                        if (
                            msg is not None
                            and not msg.is_extended_id
                            and not msg.is_error_frame
                            and not msg.is_remote_frame
                            and not msg.is_fd
                        ):
                            result = detector.feed(
                                Frame(
                                    msg.timestamp,
                                    msg.arbitration_id,
                                    tuple(msg.data),
                                    channel=args.channel,
                                )
                            )
                            if result and result["alert"]:
                                print(json.dumps(result), flush=True)
                except KeyboardInterrupt:
                    pass


if __name__ == "__main__":
    main()

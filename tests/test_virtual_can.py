"""Exercise the actual python-can adapter on an in-process virtual bus."""

import uuid
import can
import numpy as np
from cantrace.data import Encoder, Frame
from cantrace.live import StreamDetector
from cantrace.synthetic import generate


def test_python_can_virtual_ingress_scores_without_hardware():
    class Dummy:
        threshold = 0.5

        def score_samples(self, x):
            return x.mean(axis=1)

    fixture = generate(24)
    enc = Encoder(context="same_id").fit(fixture)
    detector = StreamDetector(Dummy(), enc)
    channel = "can-trace-test-" + uuid.uuid4().hex
    count = 0
    with (
        can.Bus(
            interface="virtual", channel=channel, preserve_timestamps=True
        ) as transmitter,
        can.Bus(interface="virtual", channel=channel) as receiver,
    ):
        for frame in fixture:
            transmitter.send(
                can.Message(
                    timestamp=frame.timestamp,
                    arbitration_id=frame.arbitration_id,
                    data=frame.data,
                    is_extended_id=False,
                )
            )
            msg = receiver.recv(timeout=1)
            assert msg is not None
            result = detector.feed(
                Frame(msg.timestamp, msg.arbitration_id, tuple(msg.data))
            )
            count += result is not None
    assert count == 12

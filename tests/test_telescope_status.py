import pytest

from pybrotlib.components.telescope import BROTTelescope, TelescopeStatus
from pybrotlib.transport import Transport


@pytest.mark.parametrize(
    ("ready_state", "status"),
    [
        (0.0, TelescopeStatus.PARKED),
        (0.3, TelescopeStatus.PARKING),
        (0.7, TelescopeStatus.INITIALIZING),
        (0.8, TelescopeStatus.CALIBRATING),
        (1.0, TelescopeStatus.ONLINE),
        (-1.0, TelescopeStatus.ERROR),
        (-2.0, TelescopeStatus.UNKNOWN),
    ],
)
def test_ready_state_mapping(ready_state: float, status: TelescopeStatus) -> None:
    transport = Transport()
    telescope = BROTTelescope(transport, "test")
    transport.telemetry.TELESCOPE.READY_STATE = ready_state
    assert telescope.status is status


def test_calibration_and_automatic_positioning_stay_offline_until_complete() -> None:
    transport = Transport()
    telescope = BROTTelescope(transport, "test")
    for ready_state in (0.7, 0.8, 0.8, 0.8, 1.0):
        transport.telemetry.TELESCOPE.READY_STATE = ready_state
        assert (telescope.status is TelescopeStatus.ONLINE) == (ready_state == 1.0)

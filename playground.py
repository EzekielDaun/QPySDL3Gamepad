import multiprocessing as mp
import time
from dataclasses import dataclass
from multiprocessing.synchronize import Event

from sdl3 import (
    SDL_EVENT_GAMEPAD_ADDED,
    SDL_EVENT_GAMEPAD_AXIS_MOTION,
    SDL_EVENT_GAMEPAD_BUTTON_DOWN,
    SDL_EVENT_GAMEPAD_BUTTON_UP,
    SDL_EVENT_GAMEPAD_REMOVED,
    SDL_EVENT_GAMEPAD_SENSOR_UPDATE,
    SDL_EVENT_GAMEPAD_TOUCHPAD_DOWN,
    SDL_EVENT_GAMEPAD_TOUCHPAD_MOTION,
    SDL_EVENT_GAMEPAD_TOUCHPAD_UP,
    SDL_GAMEPAD_AXIS_LEFT_TRIGGER,  # noqa: F401
    SDL_GAMEPAD_AXIS_LEFTX,  # noqa: F401
    SDL_GAMEPAD_AXIS_LEFTY,  # noqa: F401
    SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,  # noqa: F401
    SDL_GAMEPAD_AXIS_RIGHTX,  # noqa: F401
    SDL_GAMEPAD_AXIS_RIGHTY,  # noqa: F401
    SDL_GAMEPAD_BUTTON_DPAD_DOWN,  # noqa: F401
    SDL_GAMEPAD_BUTTON_DPAD_LEFT,  # noqa: F401
    SDL_GAMEPAD_BUTTON_DPAD_RIGHT,  # noqa: F401
    SDL_GAMEPAD_BUTTON_DPAD_UP,  # noqa: F401
    SDL_GAMEPAD_BUTTON_EAST,  # noqa: F401
    SDL_GAMEPAD_BUTTON_LEFT_SHOULDER,  # noqa: F401
    SDL_GAMEPAD_BUTTON_NORTH,  # noqa: F401
    SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER,  # noqa: F401
    SDL_GAMEPAD_BUTTON_SOUTH,  # noqa: F401
    SDL_GAMEPAD_BUTTON_WEST,  # noqa: F401
    SDL_INIT_GAMEPAD,
    SDL_INIT_VIDEO,
    SDL_SENSOR_ACCEL,
    SDL_SENSOR_GYRO,
    LP_SDL_Gamepad,
    SDL_CloseGamepad,
    SDL_Event,
    SDL_GamepadHasSensor,
    SDL_GetError,
    SDL_Init,
    SDL_JoystickID,
    SDL_OpenGamepad,
    SDL_SetGamepadSensorEnabled,
    SDL_WaitEventTimeout,
)
from sdl3.SDL_events import (
    SDL_GamepadAxisEvent,
    SDL_GamepadButtonEvent,
    SDL_GamepadDeviceEvent,
    SDL_GamepadSensorEvent,
    SDL_GamepadTouchpadEvent,
)


@dataclass
class GamepadState:
    axis: dict[int, int]
    button: dict[int, bool]


class Gamepad:
    def __init__(self, state_dict: dict[SDL_JoystickID, GamepadState]):
        self.stop_event = mp.Event()  # Event to signal worker to stop
        self.__state_dict = state_dict
        self.worker_process = mp.Process(
            target=self._worker, args=(self.stop_event, self.__state_dict)
        )
        self.worker_process.start()

    @staticmethod
    def _worker(stop_event: Event, state_dict: dict[SDL_JoystickID, GamepadState]):
        if not SDL_Init(SDL_INIT_GAMEPAD | SDL_INIT_VIDEO):  # type: ignore
            raise RuntimeError(f"SDL_Init failed: {SDL_GetError()}")
        while not stop_event.is_set():
            e = SDL_Event()
            if SDL_WaitEventTimeout(e, 10):  # type: ignore
                if e.type == SDL_EVENT_GAMEPAD_ADDED:  # type: ignore
                    gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                    gamepad = SDL_OpenGamepad(gamepad_device_event.which)
                    if gamepad:
                        d = state_dict
                        d[gamepad_device_event.which] = GamepadState(axis={}, button={})
                        state_dict = d

                    print(f"Gamepad {gamepad_device_event.which} added.")
                elif e.type == SDL_EVENT_GAMEPAD_REMOVED:  # type: ignore
                    gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                    if gamepad_device_event.which in state_dict:
                        del state_dict[gamepad_device_event.which]
                        SDL_CloseGamepad(gamepad_device_event.which)
                elif e.type == SDL_EVENT_GAMEPAD_AXIS_MOTION:  # type: ignore
                    axis_event: SDL_GamepadAxisEvent = e.gaxis  # type: ignore
                    if axis_event.which in state_dict:
                        d = state_dict[axis_event.which]
                        d.axis.update({axis_event.axis: axis_event.value})
                        state_dict[axis_event.which] = d


if __name__ == "__main__":
    with mp.Manager() as manager:
        state_dict = manager.dict({})
        gamepad = Gamepad(state_dict)

        try:
            while True:
                print(state_dict)
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
            # gamepad.__worker_process.terminate()
            gamepad.stop_event.set()
            gamepad.worker_process.join()
            print("Worker process terminated.")

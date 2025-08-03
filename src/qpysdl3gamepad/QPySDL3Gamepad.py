import multiprocessing
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Union

from PySide6.QtCore import QObject, QSocketNotifier, Signal
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

QPySDLGamepadEvent = Union[
    SDL_GamepadAxisEvent,
    SDL_GamepadButtonEvent,
    SDL_GamepadDeviceEvent,
    SDL_GamepadSensorEvent,
    SDL_GamepadTouchpadEvent,
]


class QPySDL3Gamepad(QObject):
    signal_sdl_event = Signal(type(QPySDLGamepadEvent))

    @staticmethod
    def _worker(
        child_conn: Connection,
        stop_event: Event,
        sdl_wait_event_timeout_ms: int,
    ):
        if not SDL_Init(SDL_INIT_GAMEPAD | SDL_INIT_VIDEO):  # type: ignore
            raise RuntimeError(f"SDL_Init failed: {SDL_GetError()}")
        else:
            gamepad_dict: dict[SDL_JoystickID, LP_SDL_Gamepad] = dict()
            while not stop_event.is_set():  # Check if the stop event is triggered
                e = SDL_Event()
                if SDL_WaitEventTimeout(e, sdl_wait_event_timeout_ms):  # type: ignore
                    if e.type == SDL_EVENT_GAMEPAD_ADDED:  # type: ignore
                        gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                        child_conn.send(gamepad_device_event)
                        gamepad = SDL_OpenGamepad(gamepad_device_event.which)
                        gamepad_dict[gamepad_device_event.which] = gamepad

                        # enable gamepad sensors
                        for sensor_type in [
                            SDL_SENSOR_ACCEL,
                            SDL_SENSOR_GYRO,
                        ]:
                            if SDL_GamepadHasSensor(gamepad, sensor_type):  # type: ignore
                                SDL_SetGamepadSensorEnabled(gamepad, sensor_type, True)  # type: ignore
                    elif e.type == SDL_EVENT_GAMEPAD_REMOVED:  # type: ignore
                        gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                        child_conn.send(gamepad_device_event)
                        gamepad = gamepad_dict.pop(gamepad_device_event.which, None)
                        if gamepad is not None:
                            SDL_CloseGamepad(gamepad)
                    elif e.type == SDL_EVENT_GAMEPAD_AXIS_MOTION:  # type: ignore
                        gamepad_axis_event: SDL_GamepadAxisEvent = e.gaxis  # type: ignore
                        child_conn.send(gamepad_axis_event)
                    elif e.type in [  # type: ignore
                        SDL_EVENT_GAMEPAD_BUTTON_DOWN,
                        SDL_EVENT_GAMEPAD_BUTTON_UP,
                    ]:
                        gamepad_button_event: SDL_GamepadButtonEvent = e.gbutton  # type: ignore
                        child_conn.send(gamepad_button_event)
                    elif e.type == SDL_EVENT_GAMEPAD_SENSOR_UPDATE:  # type: ignore
                        gamepad_sensor_event: SDL_GamepadSensorEvent = e.gsensor  # type: ignore
                        child_conn.send(gamepad_sensor_event)
                    elif e.type in [  # type: ignore
                        SDL_EVENT_GAMEPAD_TOUCHPAD_UP,
                        SDL_EVENT_GAMEPAD_TOUCHPAD_DOWN,
                        SDL_EVENT_GAMEPAD_TOUCHPAD_MOTION,
                    ]:
                        gamepad_touchpad_event: SDL_GamepadTouchpadEvent = e.gtouchpad  # type: ignore
                        child_conn.send(gamepad_touchpad_event)
                else:
                    pass  # Timeout, let it process the stop event
            child_conn.close()  # Close the pipe to indicate that the process is done

    def __init__(
        self,
        sdl_wait_event_timeout_ms: int = 50,
    ):
        super().__init__()

        self.__parent_conn, child_conn = Pipe(duplex=False)  # Create a one-way pipe
        self.__stop_event = multiprocessing.Event()  # Event to signal worker to stop
        self.__worker_process = Process(
            target=self._worker,
            args=(child_conn, self.__stop_event, sdl_wait_event_timeout_ms),
        )  # Pass the pipe connection and event
        self.__worker_process.start()

        # Create a QSocketNotifier to monitor the pipe connection for new data
        self.__notifier = QSocketNotifier(self.__parent_conn.fileno(), QSocketNotifier.Read)  # type: ignore
        self.__notifier.activated.connect(self.__read_from_pipe)

    def __read_from_pipe(self):
        if self.__parent_conn.poll():  # Check if there's data to read
            data = self.__parent_conn.recv()  # Read the data from the pipe
            if data:
                self.signal_sdl_event.emit(data)  # Emit the data to the signal

    def stop(self):
        self.__stop_event.set()  # Signal the worker to stop
        self.__worker_process.join()  # Wait for the worker process to finish
        self.__parent_conn.close()  # Close the pipe
        self.__notifier.setEnabled(False)  # Disable the QSocketNotifier

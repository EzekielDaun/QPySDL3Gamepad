from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qpysdl3gamepad.QPySDL3Gamepad import (
    SDL_EVENT_GAMEPAD_REMOVED,
    QPySDL3Gamepad,
    QPySDLGamepadEvent,
    SDL_GamepadAxisEvent,
    SDL_GamepadButtonEvent,
    SDL_GamepadDeviceEvent,
    SDL_GamepadSensorEvent,
)


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.gamepad = QPySDL3Gamepad()
        self.gamepad.signal_sdl_event.connect(self.on_sdl_event)

        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)

        self.label_dict: dict[int, QLabel] = dict()

    def on_sdl_event(self, event: QPySDLGamepadEvent):
        if event.which not in self.label_dict:
            self.label_dict[event.which] = QLabel()
            self.__layout.addWidget(self.label_dict[event.which])
        match event:
            case SDL_GamepadAxisEvent():
                s = f"SDL_GamepadAxisEvent: {event.which=}, {event.axis=}, {event.value=}"
                self.label_dict[event.which].setText(s)
                # print(s) # For Nintendo Switch Pro Controller, this event is updated too frequently
            case SDL_GamepadButtonEvent():
                s = f"SDL_GamepadButtonEvent: {event.which=}, {event.button=}, {event.down=}"
                self.label_dict[event.which].setText(s)
                print(s)
            case SDL_GamepadDeviceEvent():
                self.label_dict[event.which].setText(
                    f"SDL_GamepadDeviceEvent: {event.which=}"
                )
                if event.type == SDL_EVENT_GAMEPAD_REMOVED:
                    self.layout().removeWidget(self.label_dict[event.which])  # type: ignore
                    self.label_dict[event.which].deleteLater()
                    del self.label_dict[event.which]
            case SDL_GamepadSensorEvent():
                self.label_dict[event.which].setText(
                    f"SDL_GamepadSensorEvent: {event.which=}, {event.sensor=}, {event.data=}"
                )

    def closeEvent(self, event):
        self.gamepad.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    window = MyWindow()
    window.show()

    app.exec()

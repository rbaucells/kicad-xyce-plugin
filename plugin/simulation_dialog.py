import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QColor
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

_QML_FILE = Path(__file__).parent / "simulation_dialog.qml"
_BG = "#efefe8"


@dataclass(frozen=True)
class TransientSchedulePoint:
    time_value: str
    max_time_step_value: str


@dataclass(frozen=True)
class TransientSimulationParameters:

    initial_step_value: str
    final_time_value: str
    start_time_value: str
    step_ceiling_value: str
    op_keyword: str
    schedule_points: tuple[TransientSchedulePoint, ...]

    def to_xyce_directive(self) -> str:
        # build the required transient directive fields first
        tokens = [".TRAN", self.initial_step_value, self.final_time_value]
        # include start and step ceiling in positional order when either is provided
        if self.start_time_value or self.step_ceiling_value:
            # insert the default start time when only step ceiling was provided
            tokens.append(self.start_time_value if self.start_time_value else "0")
        # include optional step ceiling value only when provided
        if self.step_ceiling_value:
            tokens.append(self.step_ceiling_value)
        # append the selected operating-point behavior keyword when requested
        if self.op_keyword:
            tokens.append(self.op_keyword)
        # append schedule clause when schedule points are configured
        if self.schedule_points:
            # flatten alternating time and step entries for schedule syntax
            schedule_tokens = []
            # iterate all schedule points in user-provided order
            for schedule_point in self.schedule_points:
                # append the schedule time token
                schedule_tokens.append(schedule_point.time_value)
                # append the max-step token paired with that time
                schedule_tokens.append(schedule_point.max_time_step_value)
            # append the full schedule clause wrapped as a brace expression
            tokens.append("{schedule(" + ", ".join(schedule_tokens) + ")}")
        # return a single directive string that can be placed in a netlist
        return " ".join(tokens)


class SimulationDialog(QDialog):

    def __init__(self, parent: QWidget | None = None):
        # initialize the modal dialog container
        super().__init__(parent)
        # keep the result empty until the user confirms valid values
        self._result: TransientSimulationParameters | None = None
        # set dialog metadata for the native window frame
        self.setWindowTitle("Xyce Transient Simulation")
        # create the qml surface that renders the form
        self._qml_view = QQuickView()
        # connect qml-ready lifecycle hook before loading qml
        self._qml_view.statusChanged.connect(self._on_qml_ready)
        # keep the qml root sized to the embedded window container
        self._qml_view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        # match the window background to the rest of the application
        self._qml_view.setColor(QColor(_BG))
        # load the transient dialog qml component
        self._qml_view.setSource(QUrl.fromLocalFile(str(_QML_FILE)))
        # wrap the qml view in a widget so it can be hosted by qdialog
        self._container = QWidget.createWindowContainer(self._qml_view, self)
        # set up a simple one-widget dialog layout
        self._layout = QVBoxLayout(self)
        # remove margins so qml controls align edge-to-edge
        self._layout.setContentsMargins(0, 0, 0, 0)
        # insert the qml container into the dialog layout
        self._layout.addWidget(self._container)
        # set an initial size that fits the transient controls on first open
        self.resize(640, 540)

    @Slot(QQuickView.Status)
    def _on_qml_ready(self, status: QQuickView.Status) -> None:
        # skip setup until qml finishes loading
        if status != QQuickView.Status.Ready:
            return
        # capture the qml root for signal wiring and property updates
        self._root = self._qml_view.rootObject()
        # initialize defaults for a typical transient simulation setup
        self._root.setProperty("initialStep", "1u")
        self._root.setProperty("finalTime", "1m")
        self._root.setProperty("startTime", "0")
        self._root.setProperty("stepCeiling", "")
        self._root.setProperty("opModeIndex", 0)
        self._root.setProperty("scheduleEnabled", False)
        self._root.setProperty("schedulePairsText", "")
        self._root.setProperty("errorText", "")
        # connect qml submit signal to python validation and acceptance
        self._root.submit.connect(self._on_submit)
        # connect qml cancel signal to close without a result
        self._root.cancelRequested.connect(self.reject)

    @Slot(str, str, str, str, str, bool, str)
    def _on_submit(self, initial_step: str, final_time: str, start_time: str, step_ceiling: str, op_keyword: str, schedule_enabled: bool, schedule_pairs_text: str) -> None:
        # normalize user-entered values by trimming surrounding spaces
        normalized_initial_step = initial_step.strip()
        # normalize user-entered values by trimming surrounding spaces
        normalized_final_time = final_time.strip()
        # normalize optional start time while allowing an empty value
        normalized_start_time = start_time.strip()
        # normalize optional max step while allowing an empty value
        normalized_step_ceiling = step_ceiling.strip()
        # normalize operating-point mode keyword
        normalized_op_keyword = op_keyword.strip().upper()
        # normalize schedule text content
        normalized_schedule_pairs_text = schedule_pairs_text.strip()
        # enforce required transient fields before accepting the dialog
        if not normalized_initial_step or not normalized_final_time:
            # show a form-level message when required values are missing
            self._root.setProperty("errorText", "Initial step and final time are required")
            # keep dialog open for correction
            return
        # enforce allowed operating-point keywords from the transient grammar
        if normalized_op_keyword not in ["", "NOOP", "UIC"]:
            # show a form-level message when the keyword is unsupported
            self._root.setProperty("errorText", "Operating-point mode must be Default, NOOP, or UIC")
            # keep dialog open for correction
            return
        # enforce schedule input when schedule mode is enabled
        if schedule_enabled and not normalized_schedule_pairs_text:
            # show a form-level message for missing schedule pairs
            self._root.setProperty("errorText", "Schedule is enabled but no time,max-step pairs were provided")
            # keep dialog open for correction
            return
        # parse schedule pairs into structured entries when schedule mode is enabled
        try:
            # collect structured schedule entries from the user text format
            schedule_points = self._parse_schedule_points(normalized_schedule_pairs_text) if schedule_enabled else tuple()
        # handle invalid schedule format and surface a readable message to the user
        except ValueError as schedule_error:
            # show parse failure details in the form-level validation message
            self._root.setProperty("errorText", str(schedule_error))
            # keep dialog open for correction
            return
        # clear any stale validation message now that inputs are valid
        self._root.setProperty("errorText", "")
        # capture the validated dialog output for the caller
        self._result = TransientSimulationParameters(normalized_initial_step, normalized_final_time, normalized_start_time, normalized_step_ceiling, normalized_op_keyword, schedule_points)
        # close the dialog and return acceptance to the caller
        self.accept()

    def _parse_schedule_points(self, schedule_pairs_text: str) -> tuple[TransientSchedulePoint, ...]:
        # return an empty schedule when no schedule text was provided
        if not schedule_pairs_text:
            return tuple()
        # split schedule text on commas and whitespace to support flexible input
        raw_tokens = re.split(r"[\s,]+", schedule_pairs_text)
        # remove empty token fragments introduced by split boundaries
        tokens = [raw_token for raw_token in raw_tokens if raw_token]
        # enforce alternating time,max-step token pairs
        if len(tokens) % 2 != 0:
            # raise parse error with expected input format guidance
            raise ValueError("Schedule format must use time,max-step pairs")
        # initialize list used to collect structured schedule points
        schedule_points = []
        # iterate all token pairs in the original user-provided order
        for index in range(0, len(tokens), 2):
            # build one schedule point from the current token pair
            schedule_points.append(TransientSchedulePoint(tokens[index], tokens[index + 1]))
        # freeze the schedule points so dialog result stays immutable
        return tuple(schedule_points)

    def get_transient_parameters(self) -> TransientSimulationParameters | None:
        # run the modal dialog event loop and wait for user input
        dialog_code = self.exec()
        # return no value when the dialog was canceled
        if dialog_code != QDialog.DialogCode.Accepted:
            return None
        # return the previously validated transient parameter set
        return self._result

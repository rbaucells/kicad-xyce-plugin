pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    implicitWidth: 640
    implicitHeight: 540

    property alias initialStep: initialStepField.text
    property alias finalTime: finalTimeField.text
    property alias startTime: startTimeField.text
    property alias stepCeiling: stepCeilingField.text
    property alias opModeIndex: opModeComboBox.currentIndex
    property alias scheduleEnabled: scheduleEnabledCheckBox.checked
    property alias schedulePairsText: schedulePairsTextArea.text
    property string errorText: ""

    signal submit(string initialStep, string finalTime, string startTime, string stepCeiling, string opKeyword, bool scheduleEnabled, string schedulePairsText)
    signal cancelRequested()

    function opKeywordValue() {
        // map combo box index to the exact transient keyword emitted in the netlist
        if (opModeComboBox.currentIndex === 1)
            return "NOOP";
        // map combo box index to the exact transient keyword emitted in the netlist
        if (opModeComboBox.currentIndex === 2)
            return "UIC";
        // use empty token for default transient behavior
        return "";
    }

    Rectangle {
        anchors.fill: parent
        color: "#efefe8"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        Label {
            text: "Xyce Transient Simulation"
            font.pixelSize: 22
            font.bold: true
            color: "#1b1f23"
            Layout.fillWidth: true
        }

        Label {
            text: "Configure full .TRAN syntax including optional NOOP/UIC and schedule()"
            font.pixelSize: 13
            color: "#4a5560"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }

        Rectangle {
            color: "#ffffff"
            radius: 8
            border.color: "#d0d7de"
            border.width: 1
            Layout.fillWidth: true
            Layout.fillHeight: true

            GridLayout {
                anchors.fill: parent
                anchors.margins: 16
                columns: 2
                rowSpacing: 10
                columnSpacing: 12

                Label {
                    text: "Initial Step *"
                    color: "#24292f"
                }
                TextField {
                    id: initialStepField
                    placeholderText: "e.g. 1u"
                    selectByMouse: true
                    Layout.fillWidth: true
                }

                Label {
                    text: "Final Time *"
                    color: "#24292f"
                }
                TextField {
                    id: finalTimeField
                    placeholderText: "e.g. 10m"
                    selectByMouse: true
                    Layout.fillWidth: true
                }

                Label {
                    text: "Start Time"
                    color: "#24292f"
                }
                TextField {
                    id: startTimeField
                    placeholderText: "e.g. 0"
                    selectByMouse: true
                    Layout.fillWidth: true
                }

                Label {
                    text: "Step Ceiling"
                    color: "#24292f"
                }
                TextField {
                    id: stepCeilingField
                    placeholderText: "optional (defaults to (final-start)/10)"
                    selectByMouse: true
                    Layout.fillWidth: true
                }

                Label {
                    text: "Operating Point"
                    color: "#24292f"
                }
                ComboBox {
                    id: opModeComboBox
                    Layout.fillWidth: true
                    model: ["Default (compute OP)", "NOOP (skip OP)", "UIC (skip OP)"]
                }

                CheckBox {
                    id: scheduleEnabledCheckBox
                    text: "Enable schedule(time, max_step, ...)"
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                }

                Label {
                    text: "Schedule Pairs"
                    color: "#24292f"
                    enabled: scheduleEnabledCheckBox.checked
                }
                TextArea {
                    id: schedulePairsTextArea
                    placeholderText: "Enter pairs as time,max_step values.\nExample: 0.5e-3,0 1e-3,1e-6 2e-3,0"
                    selectByMouse: true
                    enabled: scheduleEnabledCheckBox.checked
                    wrapMode: TextEdit.Wrap
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                }

                Label {
                    text: root.errorText
                    visible: root.errorText.length > 0
                    color: "#b42318"
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Cancel"
                onClicked: root.cancelRequested()
            }

            Button {
                text: "Apply"
                highlighted: true
                onClicked: root.submit(root.initialStep, root.finalTime, root.startTime, root.stepCeiling, root.opKeywordValue(), root.scheduleEnabled, root.schedulePairsText)
            }
        }
    }
}

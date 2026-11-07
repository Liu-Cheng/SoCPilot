"""Paper display names; frozen benchmark identifiers and evidence stay unchanged."""

APP_LABELS = {"plate_recognition": "plate_roi", "recognition": "color_target"}


def app_label(application):
    return APP_LABELS.get(application, application)


def cpu_label(cpu):
    return "Leon3" if cpu == "LEON3" else cpu

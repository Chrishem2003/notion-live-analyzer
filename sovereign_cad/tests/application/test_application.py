from sovereign_cad.application import (
    ApplicationShell,
    ApplicationContext,
)

from sovereign_cad.application.services import (
    ApplicationService,
)


def test_application_shell():

    shell = ApplicationShell()

    assert shell.initialized is False
    assert shell.running is False

    shell.initialize()

    assert shell.initialized is True

    shell.start()

    assert shell.running is True

    shell.stop()

    assert shell.running is False


def test_service_registry():

    shell = ApplicationShell()

    service = ApplicationService(
        shell=shell
    )

    shell.register_service(
        "application",
        service,
    )

    assert shell.has_service(
        "application"
    )

    assert shell.get_service(
        "application"
    ) is service


def test_application_service():

    service = ApplicationService()

    service.set(
        "status",
        "ready",
    )

    assert service.get(
        "status"
    ) == "ready"


def test_application_context():

    context = ApplicationContext()

    context.set_metadata(
        "stage",
        7,
    )

    assert context.get_metadata(
        "stage"
    ) == 7

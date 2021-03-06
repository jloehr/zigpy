import asyncio

import asynctest
from asynctest import CoroutineMock, mock
import pytest
from zigpy import device
import zigpy.application
from zigpy.config import CONF_DATABASE, ZIGPY_SCHEMA
from zigpy.exceptions import DeliveryError
import zigpy.ota
import zigpy.types as t


@pytest.fixture
@asynctest.patch("zigpy.ota.OTA", asynctest.MagicMock(spec_set=zigpy.ota.OTA))
@asynctest.patch("zigpy.device.Device._initialize", asynctest.CoroutineMock())
def app():
    class App(zigpy.application.ControllerApplication):
        async def shutdown(self):
            pass

        async def startup(self, auto_form=False):
            pass

        async def request(
            self,
            device,
            profile,
            cluster,
            src_ep,
            dst_ep,
            sequence,
            data,
            expect_reply=True,
            use_ieee=False,
        ):
            pass

        async def permit_ncp(self, time_s=60):
            pass

    return App({CONF_DATABASE: None})


@pytest.fixture
def ieee(init=0):
    return t.EUI64(map(t.uint8_t, range(init, init + 8)))


async def test_startup():
    class App(zigpy.application.ControllerApplication):
        async def shutdown(self):
            pass

        async def request(
            self,
            device,
            profile,
            cluster,
            src_ep,
            dst_ep,
            sequence,
            data,
            expect_reply=True,
            use_ieee=False,
        ):
            pass

        async def permit_ncp(self, time_s=60):
            pass

    with pytest.raises(TypeError):
        await App({}).startup()


@mock.patch("zigpy.ota.OTA", spec_set=zigpy.ota.OTA)
async def test_new_exception(ota_mock):
    class App(zigpy.application.ControllerApplication):
        async def shutdown(self):
            pass

        async def startup(self, auto_form=False):
            pass

        async def request(
            self,
            device,
            profile,
            cluster,
            src_ep,
            dst_ep,
            sequence,
            data,
            expect_reply=True,
            use_ieee=False,
        ):
            pass

        async def permit_ncp(self, time_s=60):
            pass

    p1 = mock.patch.object(App, "_load_db", CoroutineMock())
    p2 = mock.patch.object(App, "startup", CoroutineMock())
    p3 = mock.patch.object(App, "shutdown", CoroutineMock())
    ota_mock.return_value.initialize.side_effect = CoroutineMock()

    with p1 as db_mck, p2 as start_mck, p3 as shut_mck:
        await App.new(ZIGPY_SCHEMA({CONF_DATABASE: "/dev/null"}))
    assert db_mck.call_count == 1
    assert db_mck.await_count == 1
    assert ota_mock.return_value.initialize.call_count == 1
    assert start_mck.call_count == 1
    assert start_mck.await_count == 1
    assert shut_mck.call_count == 0
    assert shut_mck.await_count == 0

    start_mck.side_effect = asyncio.TimeoutError
    with p1 as db_mck, p2 as start_mck, p3 as shut_mck:
        with pytest.raises(asyncio.TimeoutError):
            await App.new(ZIGPY_SCHEMA({CONF_DATABASE: "/dev/null"}))
    assert db_mck.call_count == 2
    assert db_mck.await_count == 2
    assert ota_mock.return_value.initialize.call_count == 2
    assert start_mck.call_count == 2
    assert start_mck.await_count == 2
    assert shut_mck.call_count == 1
    assert shut_mck.await_count == 1


async def test_form_network(app):
    with pytest.raises(NotImplementedError):
        await app.form_network()


async def test_force_remove(app):
    with pytest.raises(NotImplementedError):
        await app.force_remove(None)


async def test_request():
    class App(zigpy.application.ControllerApplication):
        async def shutdown(self):
            pass

        async def startup(self, auto_form=False):
            pass

        async def permit_ncp(self, time_s=60):
            pass

    with pytest.raises(TypeError):
        await App({}).request(None, None, None, None, None, None, None)


async def test_permit_ncp():
    class App(zigpy.application.ControllerApplication):
        async def shutdown(self):
            pass

        async def startup(self, auto_form=False):
            pass

        async def request(
            self,
            device,
            profile,
            cluster,
            src_ep,
            dst_ep,
            sequence,
            data,
            expect_reply=True,
            use_ieee=False,
        ):
            pass

    with pytest.raises(TypeError):
        await App({}).permit_ncp()


async def test_permit(app, ieee):
    ncp_ieee = t.EUI64(map(t.uint8_t, range(8, 16)))
    app._ieee = ncp_ieee
    app.devices[ieee] = mock.MagicMock()
    app.devices[ieee].zdo.permit = mock.MagicMock(
        side_effect=asyncio.coroutine(mock.MagicMock())
    )
    app.permit_ncp = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await app.permit(node=(1, 1, 1, 1, 1, 1, 1, 1))
    assert app.devices[ieee].zdo.permit.call_count == 0
    assert app.permit_ncp.call_count == 0
    await app.permit(node=ieee)
    assert app.devices[ieee].zdo.permit.call_count == 1
    assert app.permit_ncp.call_count == 0
    await app.permit(node=ncp_ieee)
    assert app.devices[ieee].zdo.permit.call_count == 1
    assert app.permit_ncp.call_count == 1


async def test_permit_delivery_failure(app, ieee):
    from zigpy.exceptions import DeliveryError

    def zdo_permit(*args, **kwargs):
        raise DeliveryError

    app.devices[ieee] = mock.MagicMock()
    app.devices[ieee].zdo.permit = zdo_permit
    app.permit_ncp = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await app.permit(node=ieee)
    assert app.permit_ncp.call_count == 0


async def test_permit_broadcast(app):
    app.broadcast = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    app.permit_ncp = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await app.permit(time_s=30)
    assert app.broadcast.call_count == 1
    assert app.permit_ncp.call_count == 1


def test_permit_with_key(app):
    with pytest.raises(NotImplementedError):
        app.permit_with_key(None, None)


async def test_join_handler_skip(app, ieee):
    app.handle_join(1, ieee, None)
    app.devices[ieee].status = device.Status.ZDO_INIT
    app.handle_join(1, ieee, None)
    assert app.devices[ieee].status == device.Status.ZDO_INIT


async def test_join_handler_change_id(app, ieee):
    app.handle_join(1, ieee, None)
    app.handle_join(2, ieee, None)
    assert app.devices[ieee].nwk == 2


async def _remove(app, ieee, retval, zdo_reply=True, delivery_failure=True):
    app.devices[ieee] = asynctest.MagicMock()

    async def leave():
        if zdo_reply:
            return retval
        elif delivery_failure:
            raise DeliveryError
        else:
            raise asyncio.TimeoutError

    app.devices[ieee].zdo.leave.side_effect = leave
    await app.remove(ieee)
    assert ieee not in app.devices


async def test_remove(app, ieee):
    app.force_remove = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await _remove(app, ieee, [0])
    assert app.force_remove.call_count == 0


async def test_remove_with_failed_zdo(app, ieee):
    app.force_remove = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await _remove(app, ieee, [1])
    assert app.force_remove.call_count == 1


async def test_remove_nonexistent(app, ieee):
    await app.remove(ieee)
    assert ieee not in app.devices


async def test_remove_with_unreachable_device(app, ieee):
    app.force_remove = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await _remove(app, ieee, [0], zdo_reply=False)
    assert app.force_remove.call_count == 1


async def test_remove_with_reply_timeout(app, ieee):
    app.force_remove = mock.MagicMock(side_effect=asyncio.coroutine(mock.MagicMock()))
    await _remove(app, ieee, [0], zdo_reply=False, delivery_failure=False)
    assert app.force_remove.call_count == 1


def test_add_device(app, ieee):
    app.add_device(ieee, 8)
    app.add_device(ieee, 9)
    assert app.get_device(ieee).nwk == 9


def test_get_device_nwk(app, ieee):
    dev = app.add_device(ieee, 8)
    assert app.get_device(nwk=8) is dev


def test_get_device_ieee(app, ieee):
    dev = app.add_device(ieee, 8)
    assert app.get_device(ieee=ieee) is dev


def test_get_device_both(app, ieee):
    dev = app.add_device(ieee, 8)
    assert app.get_device(ieee=ieee, nwk=8) is dev


def test_get_device_missing(app, ieee):
    with pytest.raises(KeyError):
        app.get_device(nwk=8)


def test_ieee(app):
    assert app.ieee == app._ieee


def test_nwk(app):
    assert app.nwk == app._nwk


def test_config(app):
    assert app.config == app._config


def test_deserialize(app, ieee):
    dev = mock.MagicMock()
    app.deserialize(dev, 1, 1, b"")
    assert dev.deserialize.call_count == 1


def test_handle_message(app, ieee):
    dev = mock.MagicMock()
    app.handle_message(dev, 260, 1, 1, 1, [])
    assert dev.handle_message.call_count == 1


def test_handle_message_uninitialized_dev(app, ieee):
    dev = device.Device(app, ieee, 0x1234)
    dev.handle_message = mock.MagicMock()
    app.handle_message(dev, 260, 1, 1, 1, [])
    assert dev.handle_message.call_count == 0

    dev.status = device.Status.ZDO_INIT
    app.handle_message(dev, 260, 1, 1, 1, [])
    assert dev.handle_message.call_count == 0

    app.handle_message(dev, 260, 0, 1, 1, [])
    assert dev.handle_message.call_count == 1


async def test_broadcast(app):
    from zigpy.profiles import zha

    with pytest.raises(NotImplementedError):
        (profile, cluster, src_ep, dst_ep, grp, radius, tsn, data) = (
            zha.PROFILE_ID,
            1,
            2,
            3,
            0,
            4,
            212,
            b"\x02\x01\x00",
        )
        await app.broadcast(
            app, profile, cluster, src_ep, dst_ep, grp, radius, tsn, data
        )


async def test_shutdown():
    class App(zigpy.application.ControllerApplication):
        async def startup(self, auto_form=False):
            pass

        async def request(
            self,
            device,
            profile,
            cluster,
            src_ep,
            dst_ep,
            sequence,
            data,
            expect_reply=True,
            use_ieee=False,
        ):
            pass

        async def permit_ncp(self, time_s=60):
            pass

    with pytest.raises(TypeError):
        await App({}).shutdown()


def test_get_dst_address(app):
    r = app.get_dst_address(mock.MagicMock())
    assert r.addrmode == 3
    assert r.endpoint == 1


async def test_update_network(app):
    with pytest.raises(NotImplementedError):
        await app.update_network()


def test_props(app):
    assert app.channel is None
    assert app.channels is None
    assert app.extended_pan_id is None
    assert app.pan_id is None
    assert app.nwk_update_id is None


async def test_mrequest(app):
    s = mock.sentinel
    with pytest.raises(NotImplementedError):
        await app.mrequest(
            s.group_id, s.profile_id, s.cluster, s.src_ep, s.sequence, s.data
        )

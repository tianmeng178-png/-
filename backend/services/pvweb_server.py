"""
Custom ParaViewWeb server entrypoint for wslink-based remote rendering.

This server registers the publish-based image delivery protocol required by
vtk.js RemoteView (viewport.image.push.* RPCs).
"""

from __future__ import annotations

import argparse
import os

from wslink import server

from paraview.web import pv_wslink
from paraview.web import protocols as pv_protocols


class _RemoteViewServer(pv_wslink.PVServerProtocol):
    dataDir = os.getcwd()
    saveDataDir = os.getcwd()
    fileToLoad = None
    authKey = "wslink-secret"
    plugins = None
    proxies = None
    colorPalette = None
    allReaders = True
    groupRegex = r"[0-9]+\.[0-9]+\.|[0-9]+\."
    excludeRegex = r"^\.|~$|^\$"

    dsHost = None
    dsPort = 11111
    rsHost = None
    rsPort = 11111
    rcPort = -1

    @classmethod
    def configure(cls, args):
        if getattr(args, "data", None):
            cls.fileToLoad = args.data
            cls.dataDir = os.path.dirname(args.data) or os.getcwd()
            cls.saveDataDir = cls.dataDir

        cls.authKey = getattr(args, "authKey", cls.authKey)
        cls.plugins = getattr(args, "plugins", None)
        cls.proxies = getattr(args, "proxies", None)
        cls.colorPalette = getattr(args, "colorPalette", None)
        cls.allReaders = not getattr(args, "noAllReaders", False)

        cls.dsHost = getattr(args, "dsHost", None)
        cls.dsPort = getattr(args, "dsPort", 11111)
        cls.rsHost = getattr(args, "rsHost", None)
        cls.rsPort = getattr(args, "rsPort", 11111)
        cls.rcPort = getattr(args, "rcPort", -1)

    def initialize(self):
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebStartupRemoteConnection(
                _RemoteViewServer.dsHost,
                _RemoteViewServer.dsPort,
                _RemoteViewServer.rsHost,
                _RemoteViewServer.rsPort,
                _RemoteViewServer.rcPort,
            )
        )
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebStartupPluginLoader(_RemoteViewServer.plugins)
        )
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebFileListing(
                _RemoteViewServer.dataDir,
                "Home",
                _RemoteViewServer.excludeRegex,
                _RemoteViewServer.groupRegex,
            )
        )
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebProxyManager(
                allowedProxiesFile=_RemoteViewServer.proxies,
                baseDir=_RemoteViewServer.dataDir,
                fileToLoad=_RemoteViewServer.fileToLoad,
                allowUnconfiguredReaders=_RemoteViewServer.allReaders,
            )
        )
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebColorManager(
                pathToColorMaps=_RemoteViewServer.colorPalette
            )
        )
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebMouseHandler())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebViewPort())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebPublishImageDelivery())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebViewPortGeometryDelivery())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebTimeHandler())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebSelectionHandler())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebWidgetManager())
        self.registerVtkWebProtocol(pv_protocols.ParaViewWebKeyValuePairStore())
        self.registerVtkWebProtocol(
            pv_protocols.ParaViewWebSaveData(baseSavePath=_RemoteViewServer.saveDataDir)
        )

        self.updateSecret(_RemoteViewServer.authKey)

        # Ensure there is an active view + representation to render.
        # Without an explicitly shown pipeline, vtk.js RemoteView may connect
        # successfully but display a blank image stream.
        if _RemoteViewServer.fileToLoad:
            try:
                from paraview.simple import (  # type: ignore
                    GetActiveViewOrCreate,
                    OpenDataFile,
                    Render,
                    ResetCamera,
                    Show,
                )

                print(f"[pvweb] Loading dataset: {_RemoteViewServer.fileToLoad}", flush=True)
                source = OpenDataFile(_RemoteViewServer.fileToLoad)
                view = GetActiveViewOrCreate("RenderView")
                Show(source, view)
                ResetCamera(view)
                Render(view)
                print("[pvweb] Dataset loaded and rendered", flush=True)
            except Exception as e:
                # Let the server continue running so the frontend can surface the error.
                print(f"[pvweb] Failed to load/render dataset: {e}", flush=True)


def _build_parser():
    parser = argparse.ArgumentParser(description="ParaViewWeb server (remote view)")
    server.add_arguments(parser)
    parser.add_argument(
        "--data",
        dest="data",
        help="Path to dataset to load (e.g. case.foam)",
    )
    parser.add_argument(
        "--plugins",
        dest="plugins",
        default=None,
        help="Plugin path(s) to load (colon-separated).",
    )
    parser.add_argument(
        "--proxies",
        dest="proxies",
        default=None,
        help="Allowed proxies file to restrict filters.",
    )
    parser.add_argument(
        "--color-palette",
        dest="colorPalette",
        default=None,
        help="Color map palette file.",
    )
    parser.add_argument(
        "--ds-host",
        dest="dsHost",
        default=None,
        help="Data server host for remote connection.",
    )
    parser.add_argument(
        "--ds-port",
        dest="dsPort",
        type=int,
        default=11111,
        help="Data server port for remote connection.",
    )
    parser.add_argument(
        "--rs-host",
        dest="rsHost",
        default=None,
        help="Render server host for remote connection.",
    )
    parser.add_argument(
        "--rs-port",
        dest="rsPort",
        type=int,
        default=11111,
        help="Render server port for remote connection.",
    )
    parser.add_argument(
        "--rc-port",
        dest="rcPort",
        type=int,
        default=-1,
        help="Reverse connect port.",
    )
    parser.add_argument(
        "--no-all-readers",
        dest="noAllReaders",
        action="store_true",
        help="Disable unconfigured readers.",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    _RemoteViewServer.configure(args)
    server.start_webserver(options=args, protocol=_RemoteViewServer)


if __name__ == "__main__":
    main()

# vtk.js + WSLink Remote View (ParaViewWeb) Design

Date: 2026-03-14

## Goal
Provide an industrial-grade, real-time 3D flow visualization inside the existing web UI by directly connecting the frontend to the ParaViewWeb wslink server running in WSL. This removes the dependency on ParaViewWeb's built-in UI and avoids iframe blank/connection issues.

## Architecture
- **Backend (WSL)**: `pvpython -m paraview.web.serve` hosts a wslink server that exposes ParaViewWeb protocols and image streaming (`/ws` endpoint).
- **Backend (API)**: `ParaViewWebService` manages lifecycle and returns `url` + `ws_url` to the frontend via WebSocket `paraview_web` messages and `/api/simulation/{id}/paraview-web`.
- **Frontend**: A new `ParaViewRemoteView` component uses `vtk.js` + `wslink` SmartConnect to establish the WebSocket session and render a remote view with interactive mouse controls.

## Components
1. **ParaViewRemoteView.tsx**
   - Builds a ws URL from `http://host:port` into `ws://host:port/ws`.
   - Creates a `vtkWSLinkClient` and `vtkRemoteView`, connects the image stream, and binds the view to a container.
   - Uses `ResizeObserver` to keep the rendering size correct.
   - Provides overlay states: idle, connecting, connected, error, closed, and a retry button.

2. **SimulationMonitor.tsx**
   - Replaces iframe with `ParaViewRemoteView`.
   - Tracks ParaViewWeb status and view connection status.
   - Uses `startTransition` and `useDeferredValue` to reduce UI jitter for residual/log updates.
   - Improves log scrolling behavior to avoid "progress jitter".

3. **ResultsPanel.tsx**
   - Migrates from `Tabs.TabPane` to `items` API and uses `destroyInactiveTabPane` to prevent chart size warnings on hidden tabs.

## Data Flow
1. Backend starts ParaViewWeb in WSL and sends `paraview_web` message with `url` and `ws_url`.
2. Frontend receives the message, stores the URL, and `ParaViewRemoteView` connects to the wslink endpoint.
3. `vtkRemoteView` streams images and supports interaction (rotate/zoom/pan) via remote mouse events.
4. Residuals + solver logs continue to stream via existing WebSocket messages.

## Error Handling
- If wslink connection fails, the view shows an error overlay with a retry button.
- If ParaViewWeb is not available, frontend remains in idle state and logs a warning.
- Log UI uses throttled state updates to avoid UI jitter.

## Testing & Verification
1. Start a real OpenFOAM run in `openfoam` mode.
2. Verify ParaViewWeb starts (`paraview_web` message contains `ws_url`).
3. Confirm the remote view connects and shows the dataset.
4. Rotate/zoom to validate interactivity.
5. Check logs and residual charts remain responsive without layout warnings.

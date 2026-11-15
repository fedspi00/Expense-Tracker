"""macOS biometric unlock via the LocalAuthentication framework (pyobjc).

Uses LAPolicyDeviceOwnerAuthentication: the system sheet leads with Touch ID
when it's enrolled and automatically offers the account password as fallback.
Degrades gracefully when pyobjc or biometrics are unavailable.
"""

try:
    from LocalAuthentication import (
        LAContext,
        LAPolicyDeviceOwnerAuthentication,
        LAPolicyDeviceOwnerAuthenticationWithBiometrics,
    )
    LA_AVAILABLE = True
except ImportError:                       # pyobjc not installed
    LA_AVAILABLE = False

# Keep the active context alive until its reply block has fired.
_active_ctx = None


def auth_available() -> bool:
    """True if this Mac can authenticate the device owner (Touch ID or password)."""
    if not LA_AVAILABLE:
        return False
    try:
        ctx = LAContext.alloc().init()
        ok, _ = ctx.canEvaluatePolicy_error_(LAPolicyDeviceOwnerAuthentication, None)
        return bool(ok)
    except Exception:
        return False


def biometrics_enrolled() -> bool:
    """True if Touch ID specifically is set up on this Mac."""
    if not LA_AVAILABLE:
        return False
    try:
        ctx = LAContext.alloc().init()
        ok, _ = ctx.canEvaluatePolicy_error_(
            LAPolicyDeviceOwnerAuthenticationWithBiometrics, None)
        return bool(ok)
    except Exception:
        return False


def authenticate(reason: str, callback) -> None:
    """Show the system Touch ID / password sheet.

    `callback(success: bool, message: str)` fires on a *background* thread —
    marshal back to Tk with widget.after(...) before touching any UI.
    """
    global _active_ctx
    if not LA_AVAILABLE:
        callback(False, "LocalAuthentication is not installed")
        return
    try:
        ctx = LAContext.alloc().init()
        ok, err = ctx.canEvaluatePolicy_error_(LAPolicyDeviceOwnerAuthentication, None)
        if not ok:
            msg = str(err.localizedDescription()) if err else "No unlock method available"
            callback(False, msg)
            return

        _active_ctx = ctx

        def reply(success, error):
            msg = ""
            if not success:
                try:
                    msg = str(error.localizedDescription()) if error else "Authentication failed"
                except Exception:
                    msg = "Authentication failed"
            callback(bool(success), msg)

        ctx.evaluatePolicy_localizedReason_reply_(
            LAPolicyDeviceOwnerAuthentication, reason, reply)
    except Exception as e:
        callback(False, str(e))

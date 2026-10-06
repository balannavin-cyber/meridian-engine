# OI-19 - Disposition Note - 2026-04-22

**Status:** CLOSED - OUT OF SCOPE.

## Finding

Resume prompt carried OI-19 as "MeridianAlpha kernel reboot (non-urgent)."

## Disposition

MeridianAlpha is an entirely separate system from MERIDIAN. Separate
repo, separate purpose (corporate actions data + Zerodha token
source for the MERIDIAN AWS consumer only). MeridianAlpha
infrastructure maintenance is not tracked in the MERIDIAN register.

Per V19 Section 3.1, MERIDIAN only consumes the Zerodha token from
MeridianAlpha via an SSH sed patch; MERIDIAN does not operate the
MeridianAlpha host.

## Action

None. OI-19 should not have been opened in the MERIDIAN OI series.
Closed without further action. If Zerodha token delivery to
MERIDIAN AWS fails in future, that will be tracked as its own
ENH or C issue in the MERIDIAN register, independent of
MeridianAlpha host state.

# OI-19 - Disposition Note - 2026-04-22

**Status:** CLOSED - OUT OF SCOPE.

## Finding

Resume prompt carried OI-19 as "MeridianAlpha kernel reboot (non-urgent)."

## Disposition

MeridianAlpha is an entirely separate system from MERDIAN. Separate
repo, separate purpose (corporate actions data + Zerodha token
source for the MERDIAN AWS consumer only). MeridianAlpha
infrastructure maintenance is not tracked in the MERDIAN register.

Per V19 Section 3.1, MERDIAN only consumes the Zerodha token from
MeridianAlpha via an SSH sed patch; MERDIAN does not operate the
MeridianAlpha host.

## Action

None. OI-19 should not have been opened in the MERDIAN OI series.
Closed without further action. If Zerodha token delivery to
MERDIAN AWS fails in future, that will be tracked as its own
ENH or C issue in the MERDIAN register, independent of
MeridianAlpha host state.

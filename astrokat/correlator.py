"""Setting correlator configuration values different from default values."""


def set_fengines(session, requant_gains=None, fft_shift=None):
    """Set the f-engine gains.

    Parameters
    ----------
    session: `SessionCBF()`
        Simplify and normalise access to a CBF stream within session
    requant_gains: int
        F-engine gain
    fft_shift: int
        Fast Fourier Transform shift

    """
    if not session.cbf.fengine.inputs:
        msg = "Cannot set the F-engine gains"
        raise RuntimeError(msg)

    for inp in session.cbf.fengine.inputs:
        # Set the gain to a single non complex number if needed
        if requant_gains is not None:
            # TODO: read and store values before assignment
            session.cbf.fengine.req.gain(inp, requant_gains)
            msg = "F-engine {} gain set to {}".format(str(inp), requant_gains)
            user_logger.info(msg)
        # Set the FFT-shift schedule
        if fft_shift is not None:
            # TODO: read and store values before assignment
            session.cbf.fengine.req.fft_shift(fft_shift)
            msg = "F-engine FFT shift schedule set to {}".format(fft_shift)
            user_logger.info(msg)
    # TODO: return input values


# -fin-

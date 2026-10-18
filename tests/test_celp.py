import unittest

import numpy as np

try:
    from teletext.celp import CELPDecoder, LtpCodebook, hamming7_dec
except ImportError:
    CELPDecoder = None


@unittest.skipIf(CELPDecoder is None, 'CELP decoding not available (needs the audio extra).')
class TestLtpCodebook(unittest.TestCase):

    def setUp(self):
        self.ltp = LtpCodebook(40)
        self.ltp.insert(np.arange(LtpCodebook.max_lag, dtype=np.double))

    def test_long_lag(self):
        # lag >= subframe length: a plain copy of the past excitation
        np.testing.assert_array_equal(self.ltp.get(50), self.ltp.history[-50:-10])

    def test_max_lag(self):
        np.testing.assert_array_equal(self.ltp.get(147), self.ltp.history[:40])

    def test_short_lag(self):
        # lag < subframe length: the last lag samples are repeated
        np.testing.assert_array_equal(self.ltp.get(20), np.tile(self.ltp.history[-20:], 2))
        np.testing.assert_array_equal(self.ltp.get(30)[30:], self.ltp.history[-30:-20])

    def test_insert(self):
        self.ltp.insert(np.full(40, -1.0))
        self.assertEqual(self.ltp.history.shape, (LtpCodebook.max_lag, ))
        np.testing.assert_array_equal(self.ltp.history[-40:], -1)


@unittest.skipIf(CELPDecoder is None, 'CELP decoding not available (needs the audio extra).')
class TestHamming(unittest.TestCase):

    def test_corrects_single_errors(self):
        valid = {d: [p for p in range(8) if hamming7_dec[d, p] == d] for d in range(16)}
        for d, parity in valid.items():
            self.assertEqual(len(parity), 1)
            for bit in range(7):
                word = ((d << 3) | parity[0]) ^ (1 << bit)
                self.assertEqual(hamming7_dec[word >> 3, word & 7], 0x10 | d)


@unittest.skipIf(CELPDecoder is None, 'CELP decoding not available (needs the audio extra).')
class TestDecoder(unittest.TestCase):

    def frames(self, n):
        rng = np.random.default_rng(1)
        return rng.integers(0, 256, size=(n, 19), dtype=np.uint8)

    def decode(self, **kwargs):
        dec = CELPDecoder(**kwargs)
        dec.last_lsf = None
        dec.last_z = np.zeros((10, ))
        dec.ltp_codebook = LtpCodebook(dec.subframe_length)
        return np.concatenate([dec.generate_audio(f) for f in self.frames(10)])

    def test_excitations(self):
        for excitation in CELPDecoder.excitation_codebooks:
            with self.subTest(excitation=excitation):
                audio = self.decode(excitation=excitation)
                self.assertEqual(audio.shape, (10 * 160, ))
                self.assertEqual(audio.dtype, np.int16)

    def test_deterministic(self):
        np.testing.assert_array_equal(self.decode(), self.decode())

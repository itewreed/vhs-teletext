CELP AUDIO
----------

Some teletext services carried compressed speech alongside the pages. The
best known example is Audetel, a UK audio description trial for blind and
partially sighted viewers in the 1990s, which sent a spoken description of the programme
in the VBI of the TV signal. The speech is coded with CELP (code-excited
linear prediction), a low bit rate speech codec, and transmitted in teletext
independent data packets.

`teletext celp` can find these packets in a t42 stream, decode them to audio
and plot statistics about them. The decoder is experimental: the bit layout
and several quantizer tables were reconstructed from published papers and
from analysing recordings, and not all of them are known. Expect noise
rather than clean speech.

CELP support needs the `audio` extra:

    pip3 install -e .[audio]

`teletext celp` is not available if `spectrum` is not installed. `play`
without `-o` also needs `miniaudio`.


FINDING CELP PACKETS
--------------------

CELP audio is sent in packets 30 and 31 of magazine 4. Teletext calls these
"data channels" (DCN), numbered 0-15: the low 3 bits are the magazine and
bit 3 selects row 30 (0) or row 31 (1).

| DCN | Packet | Content                                         |
|-----|--------|-------------------------------------------------|
| 4   | 4/30   | Programme-related audio (Audetel)               |
| 12  | 4/31   | Programme-independent audio                     |

To see whether a stream contains CELP packets, show rows 30 and 31 of
magazine 4 as text:

    teletext filter -m 4 -r 30 -r 31 -o text - stream.t42

Each CELP packet is printed as one line, for example:

    DCN: 4, Programme-related audio, S: AUDETEL, C: 0x2  8 dB  7983c1f3... 07ddc0d6...

The fields are the data channel, the type of audio, the service byte (`S`),
the control byte (`C`, with the volume level in dB and a `muted` flag) and
the two audio frames as hex. If nothing is printed the stream has no CELP
audio. Use `-o debug` instead of `-o text` to also see the packet number
and error count of each line.

Every `teletext celp` command needs the data channel to read, given with
`-d/--dcn`. Use `-d 4` for Audetel.

Some packets contain text instead of audio, sent with odd parity like normal
teletext. Test transmissions use messages such as `Audetel Test000001 Zero
fade` and `Test Talkback 0010 Address =88`, which can be read with
`-o text`. `celp play` detects these packets and outputs silence for them.

### Single and two channel modes

The service byte of DCN 12 packets selects the channel mode (see "Packet
format" below). In single channel mode the two frames of a packet follow
each other in time. In "Two-channel mode using 2 VBI lines per frame"
(service 5) frame 0 of every packet belongs to channel 1 and frame 1 to
channel 2. On recordings in this mode the LSFs and pitch of consecutive
frame 0s are related, while frame 0 and frame 1 of the same packet are as
unrelated as two random frames, and often only one channel carries speech
while the other is silent. One packet per field arrives, so each channel gets 50
frames of 20 ms per second, which is real time.

`celp play` therefore decodes only channel 1 (frame 0) of two channel
packets unless `-f` is given. Use `-f 1` for channel 2. Service 7
("Two-channel Mode using 4 VBI lines per frame") is assumed to work the same
way but has not been checked.


DECODING AUDIO
--------------

`teletext celp play` decodes the audio and plays it on the default sound
output:

    teletext celp play -d 4 stream.t42

Add `-o` to write a WAV file (8 kHz, 16 bit, mono) instead:

    teletext celp play -d 4 -o audio.wav stream.t42

Options:

* `-d/--dcn N` - data channel to decode (required, see above).
* `-o/--output FILE` - write a WAV file instead of playing the audio.
* `-f/--frame 0|1` - each packet holds two audio frames. By default both are
  decoded, in order, except in two channel mode, where only frame 0
  (channel 1) is decoded. `-f 0` or `-f 1` decodes only one of them and skips
  the other. In two channel mode this selects the channel.
* `-l/--lsf-lut ong|suddle` - quantizer table for the line spectral
  frequencies (LSF), which describe the shape of the vocal tract. Default
  `ong` (see "Open problems" for why).
* `-g/--gain-lut audetel|unknown` - quantizer table for the excitation vector
  gain. Default `audetel`.
* `-x/--excitation noise|gaussian` - stand-in for the unknown excitation
  codebook (see "Open problems" below). `noise` (default) plays running
  random noise and ignores the vector index. `gaussian` uses a fixed random
  vector for each of the 256 indexes. Both are reproducible from run to run.
* `--start`, `--stop`, `--step`, `--limit` - select a range of packets by
  position in the file, as for other commands. For example, to decode the
  part of a recording containing one programme:

      teletext celp play -d 4 --start 100000 --stop 400000 -o prog.wav stream.t42

* `--wst`, `--ts PID` - read WST or MPEG transport stream input, as for
  other commands.
* `--progress/--no-progress` - show or hide the progress bar.

While decoding, the progress bar shows two error rates, for example
`L:3%, VG:12%`:

* `L` - percentage of frames whose decoded line spectral frequencies are not
  in increasing order. Valid frames always have increasing LSFs, so these
  frames are corrupt.
* `VG` - percentage of vector gains where the Hamming check bits detected
  an error.

Both are reset each time the progress bar updates. High values mean that
the recording is damaged, that the wrong data channel was selected, or that
the quantizer tables do not match the service.

The table names refer to their sources:

| Table             | Source                                                                     |
|-------------------|----------------------------------------------------------------------------|
| `-l suddle`       | Suddle, *Speech Coding in Private and Broadcast Networks*, p. 121          |
| `-l ong`          | Ong, *Source Reliant Error Control For Low Bit Rate Speech Communications*, p. 103 |
| `-g audetel`      | Suddle, chapter 7                                                          |
| `-g unknown`      | Suddle, chapter 5                                                          |


PLOTTING STATISTICS
-------------------

`teletext celp plot` reads all CELP packets of a data channel and shows a
matplotlib window. It is a tool for working out the format, not for
listening:

    teletext celp plot -d 4 --limit 100000 stream.t42

There is one column per audio frame (0 and 1). The top row shows how often
each of the 152 bits is set, coloured by parameter, which makes the field
boundaries visible. The second row is a histogram of the vector gains
grouped by their error correction bits. The remaining rows show the pitch
gain, vector gain, pitch lag and vector index of every subframe over time.

All packets are held in memory, so use `--limit` or `--start`/`--stop` with
long recordings.


PACKET FORMAT
-------------

A CELP packet is a normal 42 byte teletext packet:

| Bytes | Content                                                          |
|-------|------------------------------------------------------------------|
| 0-1   | Magazine and row address (MRAG), magazine 4, row 30 or 31        |
| 2     | Service byte, Hamming 8/4 coded                                  |
| 3     | Control byte, Hamming 8/4 coded                                  |
| 4-22  | Audio frame 0 (19 bytes = 152 bits)                              |
| 23-41 | Audio frame 1 (19 bytes = 152 bits)                              |

For DCN 4 a service byte of 0 means Audetel. The low 3 bits of the control
byte select a level (0, 4, 8, 12, 18, 24 or 30 dB) and bit 3 mutes the
audio. For DCN 12 the service byte selects single or two channel modes, or a
user defined service if bit 3 is set.

Each audio frame is 20 ms of speech at 8000 samples per second, split into
4 subframes of 5 ms (40 samples). So one packet holds 40 ms of audio and
real time playback needs 25 packets per second. The bits of a frame are read
least significant bit first and contain:

| Bits    | Fields   | Content                                              |
|---------|----------|------------------------------------------------------|
| 0-36    | 10       | LSF indexes (widths 3, 4, 4, 4, 4, 4, 4, 4, 3, 3)    |
| 37-56   | 4 x 5    | Pitch (long term prediction) gain, one per subframe  |
| 57-76   | 4 x 5    | Excitation vector gain, one per subframe             |
| 77-104  | 4 x 7    | Pitch lag, one per subframe                          |
| 105-136 | 4 x 8    | Excitation vector index, one per subframe            |
| 137-148 | 4 x 3    | Hamming check bits for the vector gains              |
| 149-151 | 3        | Always zero in good recordings                       |

The decoder in `teletext/celp.py` works as follows:

1. The LSF indexes are looked up in the selected LSF table and interpolated
   between the previous and the current frame for each subframe.
2. The vector gains are corrected with their Hamming check bits and looked up
   in the selected gain table. Pitch gains use a fixed table.
3. The excitation for each subframe is the sum of the scaled excitation
   codebook vector and the scaled adaptive codebook vector. The adaptive
   codebook vector is the past excitation from 20-147 samples ago (pitch
   lag index + 20). When the lag is shorter than the 40 sample subframe the
   last lag samples are repeated.
4. The excitation is passed through an LPC synthesis filter built from the
   LSFs.


OPEN PROBLEMS
-------------

What is known and what is not:

| Part                     | State                                                              |
|--------------------------|--------------------------------------------------------------------|
| Bit layout               | Known, see above. Field boundaries are clearly visible in `celp plot`. |
| Vector gain Hamming code | Verified: the table is a perfect Hamming (7,4) code over the top 4 bits of each 5 bit gain, every single bit error is corrected. Covered by `tests/test_celp.py`. |
| Adaptive codebook        | Standard CELP structure, lags 20-147. The lag offset of 20 is assumed from the 7 bit field, as in FS-1016. |
| LSF tables               | Taken from Suddle and Ong. Neither is confirmed to be the table Audetel used. Measured on five two channel recordings with enough audio, `suddle` puts LSF 8 above LSF 9 in 41-81% of frames on every recording, because its row for LSF 9 (2347-3202 Hz) overlaps the row for LSF 8. `ong` does not have this problem; its out of order rate is 3-56% depending on the recording quality, mostly among LSF 2-5. `ong` is therefore the default. |
| Vector gain tables       | `audetel` from Suddle chapter 7, `unknown` from chapter 5. Not confirmed against real data. In silent passages almost all vector gains use the four smallest values. |
| Pitch lag                | Confirmed: in a recording with speech on channel 2, consecutive subframes of voiced speech have nearly the same lag (lag + 20 between 39 and 99 samples, 80-200 Hz), and the lag continues smoothly into the next frame of the same channel 70% of the time, but only 19% of the time into the other channel. Silent frames use a lag of about 80. |
| Pitch gain table         | Source not recorded in the code. Plausible: in voiced speech most pitch gains are 0.75-1.1. |
| Excitation codebook      | Unknown. Only stand-ins (`-x noise`, `-x gaussian`) are available. |

Because the excitation codebook is missing, the output keeps the rough
envelope and pitch of the original speech but sounds noisy or whispered.

The codec is described in Kondoz, "A speech coder for TV programme
description", Eurospeech 1993, pp. 257-260
(doi:10.21437/Eurospeech.1993-23), whose main contribution is "a new codebook
implementation", and in Suddle's thesis. These are the most likely sources
for the real codebook and the confirmed tables.

Once the codebook is known it can be added to
`CELPDecoder.excitation_codebooks` in `teletext/celp.py` as a (256, 40)
array, which makes it available as a new `-x` choice.

The tables can be checked against real recordings: with the right LSF table
almost no frames of a good recording should be counted in `L`, and with the
right gain tables the decoded level should follow the speech smoothly. When
comparing tables, decode the same section of a recording (`--start`,
`--stop`) with each choice and compare the `L` and `VG` rates and the sound.

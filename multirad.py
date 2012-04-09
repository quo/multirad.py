#!/usr/bin/python3

import sys, os.path, re, zipfile
from gi.repository import Gtk, Pango

RADICAL_COLS = 21
RADICAL_SIZE = 16
KANJI_SIZE = 20

RADICAL_ZIP = 'kradzip.zip'
RADICAL_FILE = 'radkfilex'
RADICAL_ENCODING = 'eucjp'
KANJI_FILE = 'kanjidic'
KANJI_ENCODING = 'eucjp'
PATHS = [os.path.dirname(sys.argv[0]), '/usr/share/edict']

def find_file(*names):
	for p in PATHS:
		for n in names:
			f = os.path.join(p, n)
			if os.path.exists(f): return f
	raise IOError('Could not find ' + ' or '.join(names))

def load_radicals():
	path = find_file(RADICAL_ZIP, RADICAL_FILE)
	if path.endswith(RADICAL_ZIP):
		lines = (s.decode(RADICAL_ENCODING) for s in zipfile.ZipFile(path).open(RADICAL_FILE))
	else:
		lines = open(f, encoding=RADICAL_ENCODING)
	radicals = []
	for s in lines:
		if s.startswith('#'): pass
		elif s.startswith('$'): # $ radical strokes jisx0212code
			s = s.split()
			char = s[1]
			if len(s) > 3:
				try:
					# decode JIS X 0212 code:
					code = int(s[3], 16) | 0x8080
					char = bytes((0x8f, code >> 8, code & 0xff)).decode('eucjp')
				except ValueError:
					try:
						char = {
							'js01': '\u2e85', # or 4ebb
							'js02': '\U000201a2', # or fe3f, 22cf
							'js03': '\u2ebe', # or 8279
							'js04': '\u2e8c',
							'js05': '\u2eb9', # or 8002
							'js07': '\u4e37',
							'kozatoR': '\xb7\u2ecf', # or 961d
							'kozatoL': '\u2ed6\xb7'  # or 961d
						}[s[3]]
					except KeyError:
						sys.stderr.write('WARNING: no mapping found for %s\n' % s[3])
			curradset = []
			radicals.append((char, int(s[2]), curradset))
		else: curradset.append(s.strip())
	return radicals

active = []
def kanjifreq(k):
	return kanjifreqs.get(k, 1<<30)
def calc_results():
	results = ''.join(sorted(frozenset.intersection(*active), key=kanjifreq)) if active else ''
	buf.set_text(results)
	status.set_text('%i radical%s selected, %i Kanji found' % (len(active), '' if len(active) == 1 else 's', len(results)))

def do_toggle(button, kanjiset):
	if button.get_active(): active.append(kanjiset)
	else: active.remove(kanjiset)
	calc_results()

# make buttons for radicals
radfont = Pango.FontDescription(str(RADICAL_SIZE))
smallradfont = Pango.FontDescription(str(RADICAL_SIZE*5//6))
widgets = []
laststrokes = None
for radical, strokes, kanjiset in load_radicals():
	if strokes != laststrokes:
		laststrokes = strokes
		widgets.append(Gtk.Label(str(strokes)))
	b = Gtk.ToggleButton(radical)
	b.props.relief = Gtk.ReliefStyle.NONE
	b.get_child().modify_font(radfont if len(radical) == 1 else smallradfont)
	b.connect('toggled', do_toggle, frozenset(''.join(kanjiset)))
	widgets.append(b)

# add buttons to table
w = RADICAL_COLS
h = (len(widgets) - 1) // w + 1
tbl = Gtk.Table(w, h)
for i, b in enumerate(widgets):
	tbl.attach(b, i%w, i%w+1, i//w, i//w+1)

# TextView for results
buf = Gtk.TextBuffer()
text = Gtk.TextView()
text.set_buffer(buf)
text.modify_font(Pango.FontDescription(str(KANJI_SIZE)))
text.props.wrap_mode = Gtk.WrapMode.CHAR
text.props.editable = False
scrolled = Gtk.ScrolledWindow()
scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
scrolled.set_shadow_type(Gtk.ShadowType.IN)
scrolled.set_size_request(-1, 50)
scrolled.add(text)

status = Gtk.Label()
status.set_alignment(0, 0)

win = Gtk.Window()
win.set_title('Multi-radical Kanji lookup')
win.connect('destroy', Gtk.main_quit)
box = Gtk.VBox()
box.pack_start(tbl, False, True, 0)
box.pack_start(scrolled, True, True, 0)
box.pack_start(status, False, True, 0)
box.set_spacing(3)
box.set_border_width(3)
win.add(box)
# done building window, show it while we finish loading:
win.show_all()
while Gtk.events_pending(): Gtk.main_iteration()

# load kanji frequencies
kanjifreqs = {}
re_freq = re.compile('^([^# ]*) .* F([0-9]*) ')
try:
	for s in open(find_file(KANJI_FILE), encoding=KANJI_ENCODING):
		freq = re_freq.findall(s)
		if freq:
			(k, freq), = freq
			kanjifreqs[k] = int(freq)
except Exception as ex:
	sys.stderr.write('WARNING: Could not load %s: %r\n' % (KANJI_FILE, ex))

calc_results()

Gtk.main()


import { useEffect, useRef, useState } from 'react';
import Snackbar from '@mui/material/Snackbar';
import MuiAlert from '@mui/material/Alert';
import './App.css';

const KEYWORDS = [
  'チビ',
  'デブ',
  'ブス',
  'キモ',
  'キツ',
  'バカ',
  'アホ',
  '死ね',
  '消えろ',
  '殺す',
  '無能',
  'クズ',
  'ゴミ',
  'ハゲ',
  'ブタ',
  'カス',
  '学歴',
  '年収',
  '障害',
  '病気',
  '収入',
  '彼氏',
  '彼女',
  '結婚',
  '離婚',
  '浮気',
  'お前',
  'おい'
];

const MARQUEE_ITEMS = [
  '配慮あるコミュニケーションを心がけましょう',
];

function App() {
  const recognizerRef = useRef(null);
  const audioRef = useRef(null);
  const restartGuardRef = useRef(false);
  const [volume, setVolume] = useState(0.5);
  const [transcript, setTranscript] = useState('');
  const [finalText, setFinalText] = useState('');
  const [alertOpen, setAlertOpen] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [cutinPlaying, setCutinPlaying] = useState(false);
  const [statusText, setStatusText] = useState('待機中');
  const [recognitionSupported, setRecognitionSupported] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    audioRef.current =
      typeof Audio !== 'undefined'
        ? new Audio(`${process.env.PUBLIC_URL}/warning01.mp3`)
        : null;

    const Recognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!Recognition) {
      setRecognitionSupported(false);
      setStatusText('このブラウザは音声認識に未対応です');
      return undefined;
    }

    const recognition = new Recognition();
    recognition.lang = 'ja-JP';
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.onstart = () => {
      setDetecting(true);
      setStatusText('音声監視中');
    };

    recognition.onend = () => {
      setDetecting(false);
      if (restartGuardRef.current) {
        try {
          recognition.start();
        } catch (error) {
          setStatusText('音声認識を再開できませんでした');
        }
      } else {
        setStatusText('待機中');
      }
    };

    recognition.onerror = () => {
      setStatusText('音声認識でエラーが発生しました');
      setDetecting(false);
    };

    recognition.onresult = (event) => {
      let latestFinal = '';

      Array.from(event.results)
        .slice(event.resultIndex)
        .forEach((result) => {
          const text = result[0].transcript.trim();

          if (result.isFinal) {
            latestFinal = text;
          } else {
            setTranscript(text);
          }
        });

      if (!latestFinal) {
        return;
      }

      setFinalText(latestFinal);
      setTranscript('');

      if (KEYWORDS.some((keyword) => latestFinal.includes(keyword))) {
        const audio = audioRef.current;
        if (audio) {
          audio.currentTime = 0;
          audio.volume = Number(volume);
          audio.play().catch(() => {});
        }
        setAlertOpen(true);
      }
    };

    recognizerRef.current = recognition;

    return () => {
      restartGuardRef.current = false;
      recognition.stop();
    };
  }, [volume]);

  useEffect(() => {
    if (!alertOpen) {
      return undefined;
    }

    setCutinPlaying(true);
    const timer = setTimeout(() => setCutinPlaying(false), 2400);
    return () => clearTimeout(timer);
  }, [alertOpen]);

  const handleRecognitionToggle = () => {
    const recognition = recognizerRef.current;

    if (!recognition) {
      return;
    }

    if (detecting) {
      restartGuardRef.current = false;
      recognition.stop();
      return;
    }

    restartGuardRef.current = true;
    try {
      recognition.start();
    } catch (error) {
      setStatusText('音声認識を開始できませんでした');
    }
  };

  return (
    <div className="app-shell">
      {cutinPlaying && (
        <div className="cutin-overlay" aria-hidden="true">
          <div className="cutin-flash"></div>
          <div className="cutin-banner">
            <div className="cutin-slice cutin-slice-top"></div>
            <div className="cutin-slice cutin-slice-bottom"></div>
            <div className="cutin-burst"></div>
            <img
              className="cutin-lines"
              src={`${process.env.PUBLIC_URL}/koukasen.png`}
              alt=""
            />
            <div className="cutin-copy">
              <div className="cutin-copy-main">WARNING</div>
              <div className="cutin-copy-sub">NON-DELI DETECTED</div>
            </div>
            <img
              className="cutin-char"
              src={`${process.env.PUBLIC_URL}/keikan.png`}
              alt=""
            />
          </div>
        </div>
      )}

      <Snackbar
        open={alertOpen}
        autoHideDuration={4000}
        onClose={() => setAlertOpen(false)}
      >
        <MuiAlert
          elevation={6}
          variant="filled"
          onClose={() => setAlertOpen(false)}
          severity="warning"
          sx={{ width: '100%' }}
        >
          危険ワードを検知しました
        </MuiAlert>
      </Snackbar>

      <header className="topbar">
        <div className="brand">Non-delicacy Alert: NKC-UG</div>
        <nav className="topnav" aria-label="Main navigation">
          <a href="#dashboard">HOME</a>
          <a href="#monitor">MONITOR</a>
          <a href="#logs">KEYWORDS</a>
        </nav>
      </header>

      <main>
        <section className="hero" id="dashboard">
          <div className="hazard-line" />
          <div className="hazard-line bottom" />
          <div className="hero-content">
            <div className="hero-logo-wrap">
              <img
                className="hero-logo"
                src={`${process.env.PUBLIC_URL}/smile.png`}
                alt="監視システムのメインビジュアル"
              />
            </div>
            <div className="hero-chip">SYSTEM STATUS: ACTIVE</div>
            <p>
              会話から不適切な発言を検知します。
            </p>
            <button
              className="btn-modern"
              type="button"
              onClick={handleRecognitionToggle}
              disabled={!recognitionSupported}
            >
              {detecting ? 'STOP SYSTEM' : 'START SYSTEM'}
            </button>
          </div>
        </section>

        <section className="marquee-section" aria-label="System alerts">
          <div className="loop-wrap">
            <div className="loop-track">
              {MARQUEE_ITEMS.map((item, index) => (
                <span key={`primary-${index}`} className="marquee-item">
                  {item}
                </span>
              ))}
            </div>
            <div className="loop-track" aria-hidden="true">
              {MARQUEE_ITEMS.map((item, index) => (
                <span key={`secondary-${index}`} className="marquee-item">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="dashboard-grid" id="monitor">
          <article className="panel panel-wide">

            <h2>検出履歴</h2>
            <p>
              リアルタイムで認識中の音声と、最後に確定したテキストを表示します。
            </p>
            <div className="transcript-box">
              <div className="transcript-row">
                <span className="transcript-title">検出状態</span>
                <strong>{statusText}</strong>
              </div>
              <div className="transcript-row">
                <span className="transcript-title">文字起こし</span>
                <span>{transcript || '...待機中'}</span>
              </div>
              {/* <div className="transcript-row">
                <span className="transcript-title">不適切発言</span>
                <span>{finalText || 'まだ検出されていません'}</span>
              </div> */}
            </div>
          </article>

          <article className="panel">
            <h2>音量調整</h2>
            <div className="volume-card">
              <img
                className="volume-icon"
                src={`${process.env.PUBLIC_URL}/volume.png`}
                alt=""
              />
              <input
                className="volume-slider"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={(event) => setVolume(Number(event.target.value))}
                aria-label="Alert volume"
              />
              <div className="volume-meta">
                <span>OUTPUT</span>
                <strong>{Math.round(volume * 100)}%</strong>
              </div>
            </div>
          </article>

          <article className="panel" id="logs">
            <h2>不適切ワード</h2>
            <p>以下のワードが含まれると警告を発火します。</p>
            <div className="keyword-list">
              {KEYWORDS.map((keyword) => (
                <span key={keyword} className="keyword-chip">
                  {keyword}
                </span>
              ))}
            </div>
          </article>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-title">Non-delicacy Alert</div>
          <div className="footer-links">
            <a href="#dashboard">HOME</a>
            <a href="#monitor">MONITOR</a>
            <a href="#logs">KEYWORDS</a>
          </div>
          <p>© 2026 NKC-UG</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

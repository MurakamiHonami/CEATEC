import './App.css';
import {React, useState, useRef,useEffect} from 'react';
import Snackbar from "@mui/material/Snackbar";
import MuiAlert from "@mui/material/Alert";


// 空文字を指定すると同一オリジン(/api/...)へのリクエストになる。
// 本番はフロントのnginxが /api/ をbackendへプロキシするため、空文字でよい。
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL ?? "http://localhost:8000";

// 音声認識の結果には前後の空白や文中の余分な空白(全角スペース含む)が混ざるため、
// バックエンドへ送る前に整形する。
const normalizeTranscript = (text) =>
  (text ?? "")
    .replace(/[\s]+/g, " ") // 改行・タブ・全角スペースなどを半角スペース1つにまとめる
    .trim();

function App() {
  const recognizerRef = useRef();
  const [volume, setVolume] = useState(0);
  const [cutinPlaying, setCutinPlaying] = useState(false);
  const [finalText, setFinalText] = useState(""); 
  const handleVolumeChange = (event) => {
    setVolume(event.target.value);
  };
  const [transcript, setTranscript] = useState("ボタンを押して検知開始"); 
  const [alertOpen, setAlertOpen] = useState(false);
  const [detecting, setDetecting] = useState(false); 
  const [sendingDashboard, setSendingDashboard] = useState(false);
  const [userMusic] = useState(null);
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    const music = new Audio('/warning01.mp3');
    const isAndroid = window.navigator.userAgent.includes("Android");
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      alert("お使いのブラウザには未対応です");
      return;
    }
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    recognizerRef.current = new SpeechRecognition();
    recognizerRef.current.lang = "ja-JP";
    recognizerRef.current.interimResults = true;
    recognizerRef.current.continuous = true;
    recognizerRef.current.onstart = () => {
      setDetecting(true);
    };
    recognizerRef.current.onend = () => {
      setDetecting(false);
      if (isAndroid && !alertOpen) {
        recognizerRef.current.start();
      }
    };
    
    // forEachのコールバックはasyncにできないため、判定処理は別のasync関数に切り出し、
    // fire-and-forget(結果を待たずに次の処理へ進む)で呼び出す形にしています。

    recognizerRef.current.onresult = event => {
      [...event.results].slice(event.resultIndex).forEach(result => {
        const transcript = result[0].transcript;
        setTranscript(transcript);
        if (result.isFinal) {

          // バックエンド(BERTモデル)による、文脈を考慮した判定
          // キーワードだけでは拾えない、皮肉や婉曲的な表現もここで検出する
          checkNondeliWithBackend(transcript);

          // 音声認識が完了して文章が確定
          setFinalText(prevState => {
            return isAndroid ? transcript : prevState;
          });
          setTranscript("発言内容を取得しています...");
        }
      });
    };

    // 判定処理を別のasync関数として切り出し
    const checkNondeliWithBackend = async (rawTranscript) => {
      const text = normalizeTranscript(rawTranscript);

      // 空白だけの認識結果はバックエンドに投げない
      if (!text) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/check-nondeli`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });

        if (!response.ok) {
          console.error("バックエンドAPIエラー:", response.status);
          return;
        }

        const data = await response.json();

        if (data.is_nondeli) {
          (userMusic || music).play();
          setAlertOpen(true);
          console.log(`ノンデリ検出: ${text} (判定根拠: ${data.reason}, 確信度: ${data.confidence})`);
        }
      } catch (error) {
        console.error("バックエンド通信エラー:", error);
        // バックエンドが落ちていても、クライアント側のキーワードチェックは
        // 既に動いているので、音声認識の体験自体は継続できる
      }
    };
  }, []);
  /* eslint-enable react-hooks/exhaustive-deps */

  // ---- ダッシュボード送信処理(コンポーネント内、他の関数と同じ場所に追加) ----
  const handleSendDashboard = async () => {
    setSendingDashboard(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/send-dashboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();
  
      if (data.success) {
        console.log("ダッシュボード送信成功:", data.message);
      } else {
        console.error("ダッシュボード送信失敗:", data.message);
        alert(`送信に失敗しました: ${data.message}`);
      }
    } catch (error) {
      console.error("ダッシュボード送信エラー:", error);
      alert("バックエンドへの接続に失敗しました");
    } finally {
      setSendingDashboard(false);
    }
  };

  useEffect(() => {
    if (alertOpen) {
      setCutinPlaying(true);
      const timer = setTimeout(() => setCutinPlaying(false), 2200);
      return () => clearTimeout(timer);
    }
  }, [alertOpen]);

  return (
    <div className="App">
      {cutinPlaying && (
        <div className="cutin-overlay" aria-hidden="true">
          <div className="cutin-flash"></div>
          <div className="cutin-banner">
            <div className="cutin-slice cutin-slice-top"></div>
            <div className="cutin-slice cutin-slice-bottom"></div>
            <div className="cutin-burst"></div>
            <img className="cutin-lines" src="koukasen.png" alt="" />
            <div className="cutin-copy">
              <div className="cutin-copy-main">WARNING</div>
              <div className="cutin-copy-sub">NON-DELI DETECTED</div>
            </div>
            <img className="cutin-char" src="keikan3.png" alt="cutin" />
          </div>
        </div>
      )}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)}>
    <MuiAlert
      elevation={6}
      variant="filled"
      onClose={() => setAlertOpen(false)}
      severity="warning"
    >
      ノンデリ発言を検出しました
    </MuiAlert>
  </Snackbar>
      <header className="App-header">
        <div className="loop-wrap">
    <ul className="loop-area">
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
    </ul>
    <ul className="loop-area">
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
    </ul>
    <ul className="loop-area">
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
        <li className="content">いつも配慮あるコミュニケーションを☺</li>
    </ul>
</div>
      </header>
      <main>
        <div style={{display:"flex", flexDirection:"column", alignItems:"center"}}>

          <img src="keikan.png" style={{height:"280px", width:"160px",marginTop:"10px"}} alt="警官の画像" /><br />
        </div>
        <div style={{display:"flex", flexDirection:"column", alignItems:"center"}}>
          <img src="volume.png" style={{height:"100px", width:"100px"}} alt="ボリュームアイコン" />
        </div>

        <input type="range" id="volumeSlider" className="input-range" min="0" max="1" step="0.1" value={volume} onChange={handleVolumeChange} />
        <p>
          {finalText}
          <span style={{ color: alertOpen ? "#f00" : "#aaa" }}>
            {transcript}
          </span>
        </p>

        <button className="btn_10" 
          onClick={detecting ? () => {
            recognizerRef.current.stop();
          }
          : () => {
                  recognizerRef.current.start();
                }}>
          <span>{detecting ? "検知中..." : "検知開始"}</span>
        </button>
        <button className="btn_10"
          disabled={sendingDashboard}
          onClick={handleSendDashboard}>
          <span>{sendingDashboard ? "送信中..." : "ダッシュボード送信"}</span>
        </button>
                
      </main>
    </div>
  );
}

export default App;

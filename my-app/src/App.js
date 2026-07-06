import './App.css';
import {React, useState, useRef,useEffect} from 'react';
import Snackbar from "@mui/material/Snackbar";
import MuiAlert from "@mui/material/Alert";


function App() {
  const recognizerRef = useRef();
  const [volume, setVolume] = useState(0);
  const [cutinPlaying, setCutinPlaying] = useState(false);
  const initialTagValues = ["年収","結婚","彼女","彼氏","病気", "障害", "低学歴", "デブ","チビ","ハゲ","キモい","キチガイ","ブス","ババア","ジジイ","ブタ","デブス","デブ女","デブ男","デブガイ","デブチビ","デブハゲ","デブキモい","デブキチガイ","デブブス","デブババア","デブジジイ","アホ","クズ","バカ","カス","ゴミ","クソ","死ね","消えろ","殺す","殺すぞ","死ねよ","死ねばいいのに","死んでしまえ","死んでくれ","ボッチ","ぼっち","ブサイク","おばさん","ババア","キモい","目障り","使えない","無能","無駄","無価値","無意味","無駄死に","無駄骨","無駄足","無駄遣い","無駄話","無駄口","無駄飯","無駄金","無駄時間","無駄労力","無駄努力","役立たず","聞かなくても分かる","お前","病気","障害","低学歴","デブ","チビ","ハゲ","キモい","キチガイ","ブス","ババア","ジジイ","ブタ","デブス","デブ女","デブ男","デブガイ","デブチビ","デブハゲ","デブキモい","デブキチガイ","デブブス","デブババア","デブジジイ","責任","甘え"]; 
  const [finalText, setFinalText] = useState(""); 
  const handleVolumeChange = (event) => {
    setVolume(event.target.value);
  };
  const [transcript, setTranscript] = useState("ボタンを押して検知開始"); 
  const [tagValues, setTagValues] = useState(initialTagValues);
  const [alertOpen, setAlertOpen] = useState(false);
  const [detecting, setDetecting] = useState(false); 
  const [userMusic, setUserMusic] = useState(null);
  useEffect(() => {
    const music = new Audio('warning01.mp3');
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
    recognizerRef.current.onresult = event => {
      [...event.results].slice(event.resultIndex).forEach(result => {
        const transcript = result[0].transcript;
        setTranscript(transcript);
        if (result.isFinal) {

          // ▼ ここから変更：バックエンド（Python）へテキストを送信
          // try {
          //   const response = await fetch("http://localhost:8000/api/check-nondeli", {
          //     method: "POST",
          //     headers: { "Content-Type": "application/json" },
          //     body: JSON.stringify({ text: transcript })
          //   });
            
          //   const data = await response.json();

          //   // バックエンドのAIが「ノンデリである（is_nondeli: true）」と判定した場合
          //   if (data.is_nondeli) {
          //     (userMusic || music).play();
          //     setAlertOpen(true);
          //     console.log(`ノンデリ検出: ${transcript} (理由: ${data.reason})`);
          //   }
          // } catch (error) {
          //   console.error("バックエンド通信エラー:", error);
          // }
          // // ▲ ここまで

            // NOTE: ユーザーが効果音を追加しなければデフォルトを鳴らす
          if (tagValues.some(value => transcript.includes(value))) {
            // NOTE: ユーザーが効果音を追加しなければデフォルトを鳴らす
            (userMusic || music).play();
            setAlertOpen(true);
          }
    
          // 音声認識が完了して文章が確定
          setFinalText(prevState => {
            // Android chromeなら値をそのまま返す
            return isAndroid ? transcript : prevState;
          });
          // 文章確定したら候補を削除
          setTranscript("");
        }
      });
    };
  }, []);

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
            <img className="cutin-char" src="keikan.png" alt="" />
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
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
    </ul>
    <ul className="loop-area">
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
    </ul>
    <ul className="loop-area">
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
        <li className="content">いつも配慮あるコミュニケーションを</li>
    </ul>
</div>
      </header>
      <main>
        <div style={{display:"flex", flexDirection:"column", alignItems:"center"}}>

          <img src="smile.png" style={{height:"280px", width:"370px",marginTop:"20px"}} alt="笑顔の画像" /><br />
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
        disabled={detecting}
          onClick={() => {
                  recognizerRef.current.start();
                }}>
          <span>{detecting ? "検知中..." : "検知開始"}</span>
        </button>
      </main>
    </div>
  );
}

export default App;

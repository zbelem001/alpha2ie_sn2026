"use client";

import { useState } from "react";
import { Megaphone, Pause, Play } from "lucide-react";
import "@/styles/flash-info.css";

// Messages du bandeau, à remplacer par les annonces de l'administration.
const announcements = [
  "Ne communiquez jamais votre code PIN ni votre code de vérification.",
  "Vérifiez toujours l’adresse du site avant de saisir vos identifiants.",
];

export function FlashInfo() {
  const [paused, setPaused] = useState(false);
  return (
    <aside className={`flash-info${paused ? " flash-info--paused" : ""}`} aria-label="Informations importantes">
      <span className="flash-info-label"><Megaphone size={15} aria-hidden="true" /> FLASH INFO</span>
      <div className="flash-info-window" id="flash-announcements">
        <div className="flash-info-track">
          {[0, 1].map((copy) => (
            <ul className="flash-info-messages" key={copy} aria-hidden={copy === 1 ? true : undefined}>
              {announcements.map((message) => <li key={message}>{message}</li>)}
            </ul>
          ))}
        </div>
      </div>
      <button className="flash-info-toggle" type="button" onClick={() => setPaused(!paused)}
        aria-controls="flash-announcements" aria-label={paused ? "Reprendre le défilement" : "Mettre le défilement en pause"}>
        {paused ? <Play size={15} aria-hidden="true" /> : <Pause size={15} aria-hidden="true" />}
      </button>
    </aside>
  );
}

"""Pages de démonstration : boîte d'envoi et téléphone simulé du citoyen.

Les données sont insérées dans la page par textContent, jamais par innerHTML :
un message ne peut pas injecter de HTML.
"""

from __future__ import annotations

import html

_STYLE = """
:root { --bg: #f4f5f7; --card: #fff; --ink: #1d2433; --muted: #667085; --line: #e3e6eb;
        --accent: #0b6e4f; --accent-soft: #e3f4ec; --danger: #b42318; --danger-soft: #fdecea; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
       font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); }
.muted { color: var(--muted); }
.badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge.sent { background: var(--accent-soft); color: var(--accent); }
.badge.failed { background: var(--danger-soft); color: var(--danger); }
button { font: inherit; cursor: pointer; border-radius: 8px; border: 1px solid var(--line);
         background: var(--card); padding: 6px 12px; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
input { font: inherit; padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; }
"""

_HELPERS = """
function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
function clock(iso) {
  return iso ? new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";
}
function prettyNumber(number) {
  const m = /^226(\\d{2})(\\d{2})(\\d{2})(\\d{2})$/.exec(number);
  return m ? `+226 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : number;
}
"""

OUTBOX_PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Boîte d'envoi simulée</title>
<style>
__STYLE__
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
header { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; justify-content: space-between; }
h1 { margin: 0; font-size: 22px; }
h2 { font-size: 16px; margin: 28px 0 8px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.table-wrap { overflow-x: auto; background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; vertical-align: top; padding: 8px 12px; border-bottom: 1px solid var(--line); }
th { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); font-weight: 600; }
tr:last-child td { border-bottom: 0; }
td.text { white-space: pre-wrap; min-width: 260px; }
td.nowrap { white-space: nowrap; }
.subject { font-weight: 600; display: block; }
.small { font-size: 12px; }
.empty { padding: 16px; color: var(--muted); }
#state { color: var(--danger); min-height: 1.4em; }
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Boîte d'envoi simulée</h1>
      <div class="muted">Aucun SMS ni e-mail n'est réellement envoyé. Mise à jour automatique.</div>
    </div>
    <div class="toolbar">
      <form id="open-phone" class="toolbar">
        <input id="phone-number" inputmode="numeric" pattern="[0-9]{8,15}" placeholder="22670000001"
               aria-label="Numéro de téléphone" required>
        <button class="primary" type="submit">Ouvrir le téléphone</button>
      </form>
      <button id="reset" type="button">Vider</button>
    </div>
  </header>
  <div id="state" role="status"></div>

  <h2>Messages envoyés</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Heure</th><th>Canal</th><th>Destinataire</th><th>Référence</th><th>Message</th><th>Statut</th></tr></thead>
    <tbody id="notifications"></tbody>
  </table></div>

  <h2>Réponses des citoyens</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Heure</th><th>Numéro</th><th>Réponse</th><th>En réponse à</th><th>Référence</th></tr></thead>
    <tbody id="replies"></tbody>
  </table></div>
</main>
<script>
__HELPERS__
function phoneLink(number) {
  const link = el("a", null, prettyNumber(number));
  link.href = "/phone/" + encodeURIComponent(number);
  return link;
}
function fill(tbody, rows, columns, emptyText) {
  tbody.replaceChildren();
  if (!rows.length) {
    const cell = el("td", "empty", emptyText);
    cell.colSpan = columns;
    tbody.append(el("tr", null, cell));
    return;
  }
  for (const row of rows) tbody.append(row);
}
function notificationRow(n) {
  const text = el("td", "text",
    n.subject ? el("span", "subject", n.subject) : null,
    n.message,
    n.reply_choices ? el("div", "small muted", "Choix proposés : " + n.reply_choices.join(" · ") +
                                               (n.answered ? " — répondu" : "")) : null);
  return el("tr", null,
    el("td", "nowrap", clock(n.sent_at)),
    el("td", null, n.channel === "sms" ? "SMS" : "E-mail"),
    el("td", "nowrap", n.channel === "sms" && n.status === "sent" ? phoneLink(n.recipient) : n.recipient),
    el("td", "nowrap", n.reference || "—"),
    text,
    el("td", null, el("span", "badge " + n.status, n.status === "sent" ? "remis" : "échec")));
}
function replyRow(r) {
  return el("tr", null,
    el("td", "nowrap", clock(r.received_at)),
    el("td", "nowrap", phoneLink(r.sender)),
    el("td", "text", r.text),
    el("td", "nowrap small", r.in_reply_to || "—"),
    el("td", "nowrap", r.reference || "—"));
}
async function refresh() {
  try {
    const [n, r] = await Promise.all([
      fetch("/notifications?limit=200").then(res => res.json()),
      fetch("/replies?limit=500").then(res => res.json()),
    ]);
    fill(document.getElementById("notifications"), n.notifications.map(notificationRow), 6, "Aucun message pour l'instant.");
    fill(document.getElementById("replies"), r.replies.reverse().map(replyRow), 5, "Aucune réponse pour l'instant.");
    document.getElementById("state").textContent = "";
  } catch (error) {
    document.getElementById("state").textContent = "Service de notifications injoignable, nouvel essai dans 3 s…";
  }
}
document.getElementById("open-phone").addEventListener("submit", (event) => {
  event.preventDefault();
  const number = document.getElementById("phone-number").value.replace(/\\D/g, "");
  if (number) window.location.href = "/phone/" + encodeURIComponent(number);
});
document.getElementById("reset").addEventListener("click", async () => {
  if (!confirm("Effacer tous les messages et réponses simulés ?")) return;
  await fetch("/simulate/reset", { method: "POST" });
  refresh();
});
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""

PHONE_PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Téléphone simulé</title>
<style>
__STYLE__
body { display: flex; flex-direction: column; align-items: center; padding: 16px; min-height: 100vh; }
.back { align-self: center; width: 100%; max-width: 380px; margin-bottom: 8px; font-size: 14px; }
.phone { width: 100%; max-width: 380px; height: min(720px, calc(100vh - 64px)); display: flex; flex-direction: column;
         background: var(--card); border: 10px solid #1d2433; border-radius: 36px; overflow: hidden;
         box-shadow: 0 12px 32px rgba(16, 24, 40, .18); }
.top { padding: 14px 16px 10px; border-bottom: 1px solid var(--line); text-align: center; }
.top strong { display: block; font-size: 16px; }
.top span { font-size: 12px; }
.thread { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; background: #f7f8fa; }
.bubble { max-width: 82%; padding: 8px 12px; border-radius: 16px; white-space: pre-wrap; overflow-wrap: anywhere; }
.bubble.in { align-self: flex-start; background: #e9ebef; border-bottom-left-radius: 4px; }
.bubble.out { align-self: flex-end; background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
.meta { display: block; font-size: 11px; opacity: .7; margin-top: 2px; }
.choices { align-self: flex-start; display: flex; gap: 8px; flex-wrap: wrap; }
.choices button { min-width: 56px; min-height: 44px; font-size: 18px; font-weight: 600; border-radius: 22px;
                  border: 2px solid var(--accent); color: var(--accent); background: var(--card); }
.empty { margin: auto; color: var(--muted); text-align: center; padding: 24px; }
form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid var(--line); }
form input { flex: 1; min-width: 0; border-radius: 20px; padding: 8px 14px; }
form button { border-radius: 20px; }
#status { min-height: 1.4em; font-size: 12px; color: var(--muted); padding: 0 12px 8px; text-align: center; }
</style>
</head>
<body data-number="__NUMBER__">
<a class="back" href="/">← Boîte d'envoi</a>
<div class="phone">
  <div class="top"><strong id="title"></strong><span class="muted">Messages (simulation)</span></div>
  <div id="thread" class="thread" aria-live="polite"></div>
  <div id="status" role="status"></div>
  <form id="composer">
    <input id="text" maxlength="160" autocomplete="off" placeholder="Répondre par SMS" aria-label="Réponse" required>
    <button class="primary" type="submit">Envoyer</button>
  </form>
</div>
<script>
__HELPERS__
const NUMBER = document.body.dataset.number;
document.getElementById("title").textContent = prettyNumber(NUMBER);
let shownSeq = -1;

function render(items) {
  const thread = document.getElementById("thread");
  thread.replaceChildren();
  if (!items.length) {
    thread.append(el("div", "empty", "Aucun SMS reçu sur ce numéro."));
    return;
  }
  for (const item of items) {
    if (item.kind === "sms") {
      thread.append(el("div", "bubble in", item.message, el("span", "meta", clock(item.sent_at))));
      if (item.reply_choices && !item.answered) {
        const choices = el("div", "choices");
        for (const choice of item.reply_choices) {
          const button = el("button", null, choice);
          button.type = "button";
          button.addEventListener("click", () => send(choice, item.notification_id));
          choices.append(button);
        }
        thread.append(choices);
      }
    } else {
      thread.append(el("div", "bubble out", item.text, el("span", "meta", clock(item.received_at))));
    }
  }
  thread.scrollTop = thread.scrollHeight;
}

async function refresh() {
  try {
    const response = await fetch("/simulate/phones/" + encodeURIComponent(NUMBER) + "/thread");
    const data = await response.json();
    const newest = data.items.length ? data.items[data.items.length - 1].seq : 0;
    if (newest !== shownSeq) {
      render(data.items);
      shownSeq = newest;
    }
  } catch (error) {
    document.getElementById("status").textContent = "Réseau simulé injoignable…";
  }
}

function deliveryText(webhook) {
  if (webhook.status === "delivered") return "Réponse transmise au backend.";
  if (webhook.status === "failed") return "Backend non joint (" + webhook.detail + ") : réponse conservée, lisible par GET /replies.";
  return "Réponse enregistrée. Le backend la lit par GET /replies.";
}

async function send(text, inReplyTo) {
  const status = document.getElementById("status");
  try {
    const response = await fetch("/simulate/replies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: NUMBER, text, in_reply_to: inReplyTo }),
    });
    const body = await response.json();
    if (!response.ok) {
      status.textContent = body.detail || "Envoi impossible.";
      return false;
    }
    status.textContent = deliveryText(body.webhook);
    await refresh();
    return true;
  } catch (error) {
    status.textContent = "Envoi impossible : service injoignable.";
    return false;
  }
}

document.getElementById("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("text");
  if (input.value.trim() && await send(input.value.trim(), null)) input.value = "";
});
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


def outbox_page() -> str:
    return OUTBOX_PAGE.replace("__STYLE__", _STYLE).replace("__HELPERS__", _HELPERS)


def phone_page(number: str) -> str:
    """`number` est validé (chiffres uniquement) par l'appelant ; échappé par précaution."""
    return (
        PHONE_PAGE.replace("__STYLE__", _STYLE)
        .replace("__HELPERS__", _HELPERS)
        .replace("__NUMBER__", html.escape(number, quote=True))
    )

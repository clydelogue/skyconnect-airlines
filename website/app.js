// ===== SCREEN NAVIGATION =====
function showScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
  window.scrollTo(0, 0);
}

// ===== LOGIN =====
document.getElementById('login-form').addEventListener('submit', function(e) {
  e.preventDefault();
  showScreen('dashboard-screen');
});

// ===== LOST BAG FORM =====
function showLostBagForm() {
  showScreen('lostbag-screen');
  nextStep(1);
}

function showFlightDetails(flightId) {
  // Placeholder — could expand later
  alert('Flight details for ' + flightId + ' — coming soon');
}

let currentStep = 1;
function nextStep(step) {
  currentStep = step;
  // Update step content
  document.querySelectorAll('.form-step').forEach(s => s.classList.remove('active'));
  document.getElementById('step-' + step).classList.add('active');
  // Update step indicators
  document.querySelectorAll('.steps-indicator .step').forEach(s => {
    const stepNum = parseInt(s.dataset.step);
    s.classList.remove('active', 'done');
    if (stepNum === step) s.classList.add('active');
    else if (stepNum < step) s.classList.add('done');
  });
}

// Bag selector click handling
document.querySelectorAll('.bag-option').forEach(opt => {
  opt.addEventListener('click', function() {
    document.querySelectorAll('.bag-option').forEach(o => o.classList.remove('selected'));
    this.classList.add('selected');
    this.querySelector('input').checked = true;
  });
});

const CASE_API_URL = 'https://8sb418qbyc.execute-api.us-east-1.amazonaws.com/prod/create-case';

function submitClaim() {
  const btn = event.target;
  btn.textContent = 'Submitting...';
  btn.disabled = true;

  // Collect form data
  const selectedBag = document.querySelector('input[name="bag"]:checked');
  const bagTag = selectedBag && selectedBag.value === 'bag1' ? 'SK8834721' : 'SK8834722';
  const bagColor = document.getElementById('bag-color').value;
  const bagType = document.getElementById('bag-type').value;
  const bagBrand = document.getElementById('bag-brand').value;
  const bagDesc = document.getElementById('bag-desc').value;
  const contents = document.getElementById('contents').value;
  const hasMedication = document.getElementById('has-medication').checked;
  const address1 = document.getElementById('address-1').value;
  const city = document.getElementById('city').value;
  const state = document.getElementById('state').value;
  const zip = document.getElementById('zip').value;

  const payload = {
    email: 'sarah.chen@email.com',
    flightNumber: 'SK-1492',
    bagTag: bagTag,
    bagDescription: `${bagColor} ${bagBrand} ${bagType}. ${bagDesc}`,
    contents: contents,
    deliveryAddress: `${address1}, ${city}, ${state} ${zip}`,
    hasMedication: hasMedication,
    caseReason: 'Lost Baggage'
  };

  fetch(CASE_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(resp => resp.json())
  .then(data => {
    btn.textContent = 'Submit Report';
    btn.disabled = false;

    if (data.success) {
      // Update confirmation screen with real case ID
      const caseIdEl = document.querySelector('.case-id');
      if (caseIdEl) caseIdEl.textContent = data.caseId;

      // Update priority badge if medical
      const priorityBadge = document.querySelector('.priority-badge');
      if (priorityBadge) {
        priorityBadge.textContent = data.priority === 'High' ? '⚕ Medical Contents — High Priority' : '📦 Standard Priority';
      }

      // Store case data for chat widget
      window.lastCaseData = {
        caseId: data.caseId,
        priority: data.priority,
        hasMedication: hasMedication,
        email: payload.email,
        flightNumber: payload.flightNumber
      };

      showScreen('confirm-screen');

      // Auto-open Connect chat widget for urgent (medication) cases
      if (hasMedication) {
        setTimeout(() => triggerProactiveChat(data), 1500);
      }
    } else {
      alert('Error creating case: ' + (data.error || 'Unknown error'));
    }
  })
  .catch(err => {
    btn.textContent = 'Submit Report';
    btn.disabled = false;
    console.error('Case creation error:', err);
    alert('Failed to submit report. Please try again.');
  });
}

// ===== PROACTIVE CHAT ENGAGEMENT =====
function triggerProactiveChat(caseData) {
  // Update Connect chat widget contact attributes with case context
  if (typeof amazon_connect === 'function') {
    amazon_connect('contactAttributes', {
      customerEmail: 'sarah.chen@email.com',
      customerName: 'Sarah Chen',
      loyaltyTier: 'SkyGold',
      caseId: caseData.caseId || '',
      priority: caseData.priority || 'Standard',
      hasMedication: 'true',
      flightNumber: 'SK-1492',
      caseReason: 'Lost Baggage'
    });
  }

  // Show proactive chat banner on confirmation screen
  showProactiveChatBanner();

  // Auto-open the Connect chat widget by clicking its button
  setTimeout(function() { openConnectChat(); }, 500);
}

function showProactiveChatBanner() {
  // Check if banner already exists
  if (document.getElementById('proactive-chat-banner')) return;

  const confirmCard = document.querySelector('.confirm-card');
  if (!confirmCard) return;

  const banner = document.createElement('div');
  banner.id = 'proactive-chat-banner';
  banner.className = 'proactive-chat-banner';
  banner.innerHTML = '<div class="proactive-chat-icon">\u2695\uFE0F\uD83D\uDCAC</div>'
    + '<div class="proactive-chat-text">'
    + '<strong>Priority Support Available</strong>'
    + '<span>Your case contains medication \u2014 chat with our priority team now for expedited help.</span>'
    + '</div>'
    + '<button class="btn btn-primary btn-sm" onclick="openConnectChat()">Chat Now</button>';

  // Insert after the confirm-notice section
  const confirmNotice = confirmCard.querySelector('.confirm-notice');
  if (confirmNotice) {
    confirmNotice.after(banner);
  } else {
    confirmCard.appendChild(banner);
  }

  // Pulse animation to draw attention
  setTimeout(() => banner.classList.add('visible'), 100);
}

function openConnectChat() {
  var btn = document.getElementById("amazon-connect-open-widget-button");
  if (btn) btn.click();
}

// ===== CHAT =====
const chatScenario = [
  {
    userMsg: null,
    botMsgs: [
      "Hi Sarah! 👋 I'm your SkyConnect AI assistant. I can see you have an open case for lost baggage on Flight SK-1492.",
      "How can I help you today?"
    ]
  },
  {
    trigger: /bag|case|when|status|update|where/i,
    botMsgs: [
      "I've pulled up your case LB-20260303-0042. Here's the latest:",
      "📍 Your bag was located at JFK International and is currently in transit to your delivery address at 425 Park Avenue, New York.",
      "🕐 Estimated delivery: Tomorrow, March 3 between 2:00–6:00 PM."
    ]
  },
  {
    trigger: /medic|pill|prescription|drug|lisinopril|blood pressure|doesn.?t arrive|what if|won.?t/i,
    botMsgs: [
      "I understand your concern — I can see your bag contains prescription medication (Lisinopril), which makes this a priority case. ⚕️",
      "For cases involving medical necessities, let me connect you with a specialist who can explore expedited delivery options and ensure your medication needs are addressed.",
      "Connecting you now — one moment..."
    ],
    action: 'escalate'
  },
  {
    trigger: /agent|human|person|speak|someone|representative|talk/i,
    botMsgs: [
      "Of course — let me connect you with a baggage specialist right away.",
      "Transferring you now..."
    ],
    action: 'escalate'
  }
];

let chatStep = 0;
let chatInitialized = false;
let isEscalated = false;

function openChat() {
  const widget = document.getElementById('chat-widget');
  const fab = document.getElementById('chat-fab');
  widget.classList.remove('hidden');
  fab.classList.add('hidden');
  
  if (!chatInitialized) {
    chatInitialized = true;
    // Show welcome messages
    setTimeout(() => addBotMessages(chatScenario[0].botMsgs), 600);
    chatStep = 1;
  }
}

function closeChat() {
  document.getElementById('chat-widget').classList.add('hidden');
  document.getElementById('chat-fab').classList.remove('hidden');
}

function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || isEscalated) return;
  
  addMessage(text, 'user');
  input.value = '';
  
  // Find matching scenario
  let matched = false;
  for (let i = chatStep; i < chatScenario.length; i++) {
    if (chatScenario[i].trigger && chatScenario[i].trigger.test(text)) {
      showTyping();
      setTimeout(() => {
        removeTyping();
        addBotMessages(chatScenario[i].botMsgs);
        if (chatScenario[i].action === 'escalate') {
          setTimeout(() => escalateToAgent(), 2000);
        }
        chatStep = i + 1;
      }, 1500);
      matched = true;
      break;
    }
  }
  
  // Default response if no match
  if (!matched) {
    showTyping();
    setTimeout(() => {
      removeTyping();
      addBotMessages(["I'd be happy to help with that! Could you tell me more about your concern regarding your lost bag on Flight SK-1492?"]);
    }, 1000);
  }
}

function addMessage(text, type) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = 'msg ' + type;
  if (type === 'bot') {
    msg.innerHTML = '<span class="sender">SkyConnect AI</span>' + text;
  } else {
    msg.textContent = text;
  }
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function addBotMessages(messages, delay = 600) {
  messages.forEach((msg, i) => {
    setTimeout(() => addMessage(msg, 'bot'), i * delay);
  });
  // Scroll after last message
  setTimeout(() => {
    document.getElementById('chat-messages').scrollTop = 999999;
  }, messages.length * delay + 100);
}

function showTyping() {
  const container = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.id = 'typing';
  typing.innerHTML = '<span></span><span></span><span></span>';
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;
}

function removeTyping() {
  const typing = document.getElementById('typing');
  if (typing) typing.remove();
}

function escalateToAgent() {
  isEscalated = true;
  const container = document.getElementById('chat-messages');
  
  // System message
  const sys = document.createElement('div');
  sys.className = 'msg bot';
  sys.style.background = '#fef3c7';
  sys.style.borderLeft = '3px solid #f59e0b';
  sys.innerHTML = '<span class="sender" style="color:#92400e">System</span>🔄 Connecting to a SkyConnect baggage specialist...';
  container.appendChild(sys);
  
  setTimeout(() => {
    const agent = document.createElement('div');
    agent.className = 'msg bot';
    agent.style.background = '#ecfdf5';
    agent.style.borderLeft = '3px solid #10b981';
    agent.innerHTML = '<span class="sender" style="color:#065f46">Agent: Marcus J.</span>Hi Sarah, I\'m Marcus from the SkyConnect Baggage Priority team. I can see your case and that you have medication in your bag. Let me look into expedited delivery options for you right now.';
    container.appendChild(agent);
    container.scrollTop = container.scrollHeight;
    
    // Re-enable input for chatting with agent
    isEscalated = false;
    document.getElementById('chat-input').placeholder = 'Chat with Marcus J...';
  }, 2500);
}

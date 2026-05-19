/**
 * /api/contact — Vercel serverless function
 *
 * Receives the Get-in-touch form submission, validates it, and sends
 * an email via Resend (https://resend.com) to the configured recipient.
 *
 * Environment variables (set in Vercel project Settings → Env Vars):
 *
 *   RESEND_API_KEY      Required. Your Resend API key (re_…).
 *                       Generate at https://resend.com/api-keys
 *
 *   CONTACT_RECIPIENT   Optional. Email address to deliver to.
 *                       Defaults to "efaz.mintu@gmail.com" (testing).
 *                       Set to "info@nvhltd.com" for production.
 *
 *   RESEND_FROM         Optional. The From: header Resend will send.
 *                       Defaults to "NVH Website <onboarding@resend.dev>"
 *                       which is Resend's shared default sender
 *                       (works without domain verification, but
 *                       lower deliverability). For production, verify
 *                       nvhltd.com in Resend's dashboard and set this
 *                       to e.g. "NVH <contact@nvhltd.com>".
 */

// Defensive HTML escape for inserting form values into the email body.
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export default async function handler(req, res) {
  // Method gate
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ success: false, message: 'Method not allowed' });
  }

  // Vercel auto-parses application/json into req.body. If the client
  // sent x-www-form-urlencoded, req.body would already be parsed too.
  // If the client somehow sent raw text, fall back to manual parse.
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  const {
    fullName = '',
    email    = '',
    phone    = '',
    location = '',
    message  = '',
    _honey   = ''
  } = body;

  // Honeypot: real users don't fill _honey (it's an invisible field).
  // If filled, pretend success and silently discard.
  if (_honey) {
    return res.status(200).json({ success: true });
  }

  // Validation. Required fields per the form markup.
  const name  = String(fullName).trim();
  const mail  = String(email).trim();
  const ph    = String(phone).trim();
  const loc   = String(location).trim();
  const msg   = String(message).trim();

  if (!name || !mail || !ph) {
    return res.status(400).json({
      success: false,
      message: 'Please fill in your name, email, and phone number.'
    });
  }
  // Basic email shape check
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) {
    return res.status(400).json({
      success: false,
      message: 'That email address looks invalid.'
    });
  }

  // Resolve env config
  const apiKey    = process.env.RESEND_API_KEY;
  const recipient = process.env.CONTACT_RECIPIENT || 'efaz.mintu@gmail.com';
  const fromAddr  = process.env.RESEND_FROM       || 'NVH Website <onboarding@resend.dev>';

  if (!apiKey) {
    console.error('[contact] Missing RESEND_API_KEY env var');
    return res.status(500).json({
      success: false,
      message: 'Server is missing email configuration. Please email us directly.'
    });
  }

  const subject = `NVH Shareholder Enquiry — ${name}`;

  // Plain-text body for clients that don't render HTML.
  const textBody = [
    'New shareholder enquiry from the NVH website:',
    '',
    `Full name: ${name}`,
    `Email:     ${mail}`,
    `Phone:     ${ph}`,
    `Location:  ${loc || '—'}`,
    '',
    'Message:',
    msg || '(no message)',
    '',
    '—',
    'Sent via the New Vision Housing contact form.'
  ].join('\n');

  // HTML body — clean table layout
  const htmlBody = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; color: #1a1a1a;">
      <h2 style="font-family: Georgia, serif; font-weight: 400; color: #0F3D34; border-bottom: 2px solid #b08d57; padding-bottom: 8px;">
        New shareholder enquiry
      </h2>
      <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr><th style="text-align:left; padding:8px; background:#f4ece1; width:120px;">Full name</th><td style="padding:8px; border-bottom:1px solid #eee;">${escapeHtml(name)}</td></tr>
        <tr><th style="text-align:left; padding:8px; background:#f4ece1;">Email</th><td style="padding:8px; border-bottom:1px solid #eee;"><a href="mailto:${escapeHtml(mail)}">${escapeHtml(mail)}</a></td></tr>
        <tr><th style="text-align:left; padding:8px; background:#f4ece1;">Phone</th><td style="padding:8px; border-bottom:1px solid #eee;">${escapeHtml(ph)}</td></tr>
        <tr><th style="text-align:left; padding:8px; background:#f4ece1;">Location</th><td style="padding:8px; border-bottom:1px solid #eee;">${escapeHtml(loc) || '<span style="color:#999;">—</span>'}</td></tr>
      </table>
      <h3 style="font-family: Georgia, serif; font-weight: 400;">Message</h3>
      <p style="background:#fafafa; padding:14px; border-left:3px solid #b08d57; white-space:pre-wrap; line-height:1.6;">${escapeHtml(msg) || '<span style="color:#999;">(no message)</span>'}</p>
      <p style="font-size:12px; color:#777; margin-top:24px; text-align:center;">
        Sent via the New Vision Housing contact form.
      </p>
    </div>
  `;

  try {
    const resendResp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization:  `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from:     fromAddr,
        to:       [recipient],
        reply_to: mail,
        subject:  subject,
        text:     textBody,
        html:     htmlBody
      })
    });

    const raw = await resendResp.text();
    let data = null;
    try { data = raw ? JSON.parse(raw) : null; } catch (e) { /* keep raw */ }

    if (!resendResp.ok) {
      console.error('[contact] Resend API error', resendResp.status, raw);
      return res.status(502).json({
        success: false,
        message: (data && data.message) || `Email service returned ${resendResp.status}`
      });
    }

    return res.status(200).json({ success: true, id: data && data.id });
  } catch (err) {
    console.error('[contact] Fetch error', err);
    return res.status(500).json({
      success: false,
      message: 'Could not reach email service. Please try again or email us directly.'
    });
  }
}

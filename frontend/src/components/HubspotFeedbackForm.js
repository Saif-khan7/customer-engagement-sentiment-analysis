// frontend/src/components/HubspotFeedbackForm.js
import { useEffect, useState } from "react";

// HubSpot creds
const REGION   = "na2";
const PORTAL   = "242997037";
const FORM_ID  = "e28f30f4-9c5c-4dff-9412-1e8b1a2acc04";

export default function HubspotFeedbackForm() {
  const [sentiment, setSentiment] = useState(null);

  useEffect(() => {
    let cancelled = false;

    /** Ensure the v2 library is on the page, then create the form */
    const ensureLibAndCreate = () => {
      if (cancelled) return;

      if (window.hbspt?.forms?.create) {
        // avoid duplicate creation in StrictMode
        if (window.__hubspotFormLoaded) return;
        window.__hubspotFormLoaded = true;

        window.hbspt.forms.create({
          region:   REGION,
          portalId: PORTAL,
          formId:   FORM_ID,
          target:   "#hs-form-wrapper",
          onFormSubmitted: async (_, fields) => {
            const msg =
              fields.find(f => f.name === "message")?.value || "";
            if (!msg) return;

            try {
              const res = await fetch(
                `${process.env.REACT_APP_API_BASE || ""}/api/sentiment`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ text: msg })
                }
              );
              const data = await res.json();    // {label, score}
              setSentiment(data);
            } catch (err) {
              console.error("Sentiment API error", err);
            }
          }
        });
        return;
      }

      /* If the library isn’t there yet, load it. */
      const script = document.createElement("script");
      script.src   = "//js.hsforms.net/forms/v2.js";
      script.async = true;
      script.onload = ensureLibAndCreate;  // try again when loaded
      document.body.appendChild(script);
    };

    ensureLibAndCreate();

    return () => { cancelled = true; };
  }, []);

  return (
    <div className="space-y-6">
      <div id="hs-form-wrapper" />
      {sentiment && (
        <div className="p-4 rounded-xl shadow bg-gray-50 text-center">
          <p className="font-semibold">Sentiment detected:</p>
          <p className="text-2xl">{sentiment.label}</p>
          <p className="text-sm opacity-70">
            confidence {(sentiment.score * 100).toFixed(1)}%
          </p>
        </div>
      )}
    </div>
  );
}

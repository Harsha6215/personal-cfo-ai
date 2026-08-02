import { useState } from "react";

const FEEDBACK_TYPES = [
  { value: "bug", label: "Bug" },
  { value: "feature", label: "Feature" },
  { value: "ai_rating", label: "AI Rating" },
  { value: "general", label: "General" },
] as const;

type FeedbackType = (typeof FEEDBACK_TYPES)[number]["value"];

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<FeedbackType>("general");
  const [content, setContent] = useState("");
  const [rating, setRating] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!content.trim()) return;
    setSubmitting(true);

    try {
      const token = localStorage.getItem("access_token");
      const body: Record<string, unknown> = {
        feedback_type: type,
        content: content.trim(),
        page: window.location.pathname,
      };
      if (type === "ai_rating" && rating > 0) {
        body.rating = rating;
      }

      await fetch("/api/v1/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });

      setSubmitted(true);
      setTimeout(() => {
        setOpen(false);
        setSubmitted(false);
        setContent("");
        setRating(0);
        setType("general");
      }, 1500);
    } catch {
      // Fail silently — feedback is non-critical
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg transition-transform hover:scale-110 hover:bg-indigo-700"
        aria-label="Send feedback"
      >
        <span className="text-xl">💬</span>
      </button>
    );
  }

  if (submitted) {
    return (
      <div className="fixed bottom-6 right-6 z-50 w-80 rounded-xl bg-white p-6 shadow-2xl dark:bg-slate-800">
        <p className="text-center text-lg font-medium text-green-600 dark:text-green-400">
          Thanks! 🎉
        </p>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80 rounded-xl bg-white p-4 shadow-2xl dark:bg-slate-800">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          Send Feedback
        </h3>
        <button
          onClick={() => setOpen(false)}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          aria-label="Close feedback"
        >
          ✕
        </button>
      </div>

      {/* Type selector */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {FEEDBACK_TYPES.map((ft) => (
          <button
            key={ft.value}
            onClick={() => setType(ft.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              type === ft.value
                ? "bg-indigo-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300"
            }`}
          >
            {ft.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Tell us what's on your mind..."
        className="mb-3 w-full resize-none rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-500"
        rows={3}
      />

      {/* Star rating — only for ai_rating */}
      {type === "ai_rating" && (
        <div className="mb-3 flex items-center gap-1">
          <span className="mr-2 text-xs text-slate-500 dark:text-slate-400">
            Rating:
          </span>
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => setRating(star)}
              className={`text-lg transition ${
                star <= rating
                  ? "text-yellow-400"
                  : "text-slate-300 dark:text-slate-600"
              }`}
              aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
            >
              ★
            </button>
          ))}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={submitting || !content.trim()}
        className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? "Sending..." : "Submit"}
      </button>
    </div>
  );
}

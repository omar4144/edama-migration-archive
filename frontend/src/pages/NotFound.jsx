import React from "react";
import { Link } from "react-router-dom";
export default function NotFound() {
  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center" data-testid="not-found">
      <div className="text-center">
        <div className="text-6xl font-mono text-navy/30 mb-4">404</div>
        <div className="text-navy/70 mb-6">الصفحة غير موجودة</div>
        <Link to="/" className="btn-primary">العودة للرئيسية</Link>
      </div>
    </div>
  );
}

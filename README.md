# Today Tasks (PWA)

تطبيق مهام بسيط (PWA) يشتغل Offline. الاستخدام الأساسي بدون تسجيل، مع خيار تسجيل اختياري لربط Google Calendar.

## الميزات
- تخزين محلي عبر IndexedDB
- إدخال سريع بالعربي: مثال `بكرا اجتماع 10` → مهمة لليوم/بكرا + وقت
- تثبيت المهام (Pin) + ترتيب تلقائي
- مشاركة قائمة اليوم برابط (يحتوي البيانات مضغوطة)
- لكل مهمة: إضافة للتقويم (Google Calendar Template) + تنزيل ICS
- تسجيل اختياري:
  - Sign in via Google (Profile)
  - ربط Google Calendar (OAuth) + زر "Sync pinned"
- PWA: قابل للتثبيت + Offline cache

## تشغيل محلياً
```bash
npm install
npm run dev
```

## تفعيل Google Login + Google Calendar (اختياري)
1) انسخ `.env.example` إلى `.env` وضع `VITE_GOOGLE_CLIENT_ID`.
2) في Google Cloud Console:
   - OAuth Client (Web)
   - Authorized JavaScript origins: `http://localhost:5173` (وأي دومين إنتاج)

> بدون هذه الخطوات، التطبيق يعمل طبيعي لكن بدون تسجيل/مزامنة تقويم.

## بناء نسخة إنتاج
```bash
npm run build
npm run preview
```

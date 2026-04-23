# Contest Setup Guide — Firebase + Google Sign-In

## 1. Create a Firebase Project

1. Go to https://console.firebase.google.com/
2. Click **Add project** → name it `to1000-contest`
3. Disable Google Analytics (optional, not needed)
4. Click **Create project**

## 2. Enable Google Authentication

1. In your Firebase project, go to **Authentication** → **Sign-in method**
2. Click **Google** → Enable it
3. Set a support email (your email)
4. Click **Save**
5. Go to **Authentication** → **Settings** → **Authorized domains**
6. Add `to1000.com` and `www.to1000.com`

## 3. Create Firestore Database

1. Go to **Firestore Database** → **Create database**
2. Choose **Start in production mode**
3. Select a region close to your audience (e.g., `us-central1` or `europe-west1`)

## 4. Set Firestore Security Rules

Go to **Firestore Database** → **Rules** and paste:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Predictions: one document per user (doc ID = user UID)
    match /predictions/{uid} {
      // Anyone authenticated can read their own prediction
      allow read: if request.auth != null && request.auth.uid == uid;

      // Can only create (not update/delete) their own prediction
      allow create: if request.auth != null
                    && request.auth.uid == uid
                    && request.resource.data.keys().hasAll(['week', 'displayName', 'email', 'createdAt'])
                    && request.resource.data.week is string
                    && request.resource.data.week.size() > 0;

      // No updates or deletes — one vote, final
      allow update, delete: if false;
    }

    // Stats: public read, no client writes
    match /contest_stats/{doc} {
      allow read: if true;
      allow write: if false;
    }

    // Block everything else
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Click **Publish**.

## 5. Get Your Firebase Config

1. Go to **Project settings** (gear icon) → **General**
2. Scroll to **Your apps** → Click **Web** (</>) icon
3. Register app with nickname `to1000-web`
4. Copy the `firebaseConfig` object. It looks like:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "to1000-contest.firebaseapp.com",
  projectId: "to1000-contest",
  storageBucket: "to1000-contest.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

## 6. Update index.html

In `index.html`, find this block (search for `FIREBASE_CONFIG`):

```javascript
const FIREBASE_CONFIG = {
  apiKey: "YOUR_API_KEY",
  ...
};
```

Replace the placeholder values with your real Firebase config values.

## 7. Deploy

From PowerShell, in the `to1000` folder:

```powershell
npx wrangler pages deploy public/ --project-name to1000 --branch main
```

## 8. Test

1. Open https://to1000.com
2. Scroll to the "Predict & Win" section
3. Click "Sign in with Google"
4. Pick a week and submit
5. Try submitting again — it should say you already voted
6. Check Firestore console → `predictions` collection to see the entry

## Troubleshooting

- **Google Sign-In popup blocked**: Make sure `to1000.com` is in Firebase Authorized Domains
- **Permission denied on Firestore**: Double-check the security rules are published
- **Firebase SDK not loading**: The site uses CDN imports from `https://www.gstatic.com/firebasejs/11.0.0/` — make sure your network/CDN allows this

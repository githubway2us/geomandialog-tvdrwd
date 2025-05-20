// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAiRbjU28fDDKZTbWsEEkUzSIvSxP07K-o",
  authDomain: "geomandialog-tvdrwd-native.firebaseapp.com",
  projectId: "geomandialog-tvdrwd-native",
  storageBucket: "geomandialog-tvdrwd-native.firebasestorage.app",
  messagingSenderId: "354980866035",
  appId: "1:354980866035:web:bdb51723aec716c3411486",
  measurementId: "G-VYDWC7KZ0J"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
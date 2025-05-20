// public/static/firebase.js
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyDwy_G9gd_7e3mlMLWvi4Gd6RTG7ticeNI",
    authDomain: "geomandialog-tvdrwd.firebaseapp.com",
    databaseURL: "https://geomandialog-tvdrwd.firebaseio.com",
    projectId: "geomandialog-tvdrwd",
    storageBucket: "geomandialog-tvdrwd.firebasestorage.app",
    messagingSenderId: "604583179475",
    appId: "1:604583179475:web:190d598adbdb0f957f9026"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

export { db, auth };
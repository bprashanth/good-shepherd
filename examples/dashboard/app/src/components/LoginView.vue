<template>
  <div class="login-container">
    <div class="blur-overlay">
      <div class="login-box">
        <button class="login-button" @click="signInWithGoogle">
          Login
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const whitelist = [
  '*@tech4goodcommunity.com',
  '*@ncf-india.org',
];

// Returns true if the email is in the whitelist.
// The whitelist can contain patterns like:
// - 'xyz@tech4goodcommunity.com'
// - '*@tech4goodcommunity.com'
// - 'prashanthseven@gmail.com'
function isEmailAllowed(email) {
  return whitelist.some(pattern => {
    if (pattern.startsWith('*@')) {
      const domain = pattern.substring(1);
      return email.endsWith(domain);
    }
    return pattern === email;
  });
}

function signInWithGoogle() {

  // For staging previews, we can just set the user to a fake email.
  if (window.location.hostname.includes('deploy-preview')) {
    localStorage.setItem('user', JSON.stringify({ email: 'dev@fake.com' }));
    router.push(route.query.redirect || '/');
    return;
  }

  const tokenClient = window.google.accounts.oauth2.initTokenClient({
    // The client ID is a public identifier for apps. It is safe to include
    // it in publicly accessible code:
    // https://developers.google.com/identity/branding-guidelines
    client_id: '110256244948-43jro97hujn4huhlv0kms0o6f8qcoi25.apps.googleusercontent.com',
    scope: 'email profile',
    callback: (response) => {
      fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
        headers: {
          Authorization: `Bearer ${response.access_token}`,
        }
      })
      .then(res => res.json())
      .then(user => {
        if (isEmailAllowed(user.email)) {
          localStorage.setItem('user', JSON.stringify(user));
          router.push(route.query.redirect || '/');
        } else {
          alert('Access denied')
        }
      })
    }
  })
  tokenClient.requestAccessToken();
}


</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  background: url('../assets/fish.webp') no-repeat center center;
  background-size: cover;
  background-attachment: fixed;
}

.blur-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.2);
  z-index: 1;
}

.login-box {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.login-button {
  font-size: 1.2em;
  padding: 1em 2em;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.2);

  border: none;
  color: rgb(21, 21, 21, 0.5);
  cursor: pointer;
  position: relative;
  background-color: transparent;
  color: #1E628C;
}
</style>
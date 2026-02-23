import { ref, computed } from 'vue'
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from 'amazon-cognito-identity-js'

const AUTH_CONFIG_URL =
  'https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json'

let userPool = null
const idToken = ref(null)
const authError = ref(null)
const isAuthenticated = computed(() => !!idToken.value)

async function init() {
  if (userPool) return
  const res = await fetch(AUTH_CONFIG_URL)
  const config = await res.json()
  userPool = new CognitoUserPool({
    UserPoolId: config.userPoolId,
    ClientId: config.clientId,
  })
}

function login(username, password) {
  return new Promise((resolve, reject) => {
    if (!userPool) {
      reject(new Error('Auth not initialised — call init() first'))
      return
    }
    authError.value = null
    const user = new CognitoUser({ Username: username, Pool: userPool })
    const authDetails = new AuthenticationDetails({
      Username: username,
      Password: password,
    })
    user.authenticateUser(authDetails, {
      onSuccess(session) {
        idToken.value = session.getIdToken().getJwtToken()
        resolve()
      },
      onFailure(err) {
        authError.value = err.message || 'Login failed'
        reject(err)
      },
    })
  })
}

function refreshSession() {
  return new Promise((resolve) => {
    if (!userPool) {
      resolve(false)
      return
    }
    const user = userPool.getCurrentUser()
    if (!user) {
      idToken.value = null
      resolve(false)
      return
    }
    user.getSession((err, session) => {
      if (err || !session || !session.isValid()) {
        idToken.value = null
        resolve(false)
        return
      }
      idToken.value = session.getIdToken().getJwtToken()
      resolve(true)
    })
  })
}

function logout() {
  if (userPool) {
    const user = userPool.getCurrentUser()
    if (user) user.signOut()
  }
  idToken.value = null
  authError.value = null
}

export function useCognitoAuth() {
  return {
    init,
    login,
    refreshSession,
    logout,
    idToken,
    isAuthenticated,
    authError,
  }
}

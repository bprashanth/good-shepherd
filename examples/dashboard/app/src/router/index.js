import { createRouter, createWebHistory } from 'vue-router';
import DashboardComponent from '../components/DashboardComponent.vue';
import LoginView from '../components/LoginView.vue';
import App from '../App.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: App
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardComponent,
    props: true
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const user = JSON.parse(localStorage.getItem('user'));
  if (!user && to.name !== 'Login') {
    next({ name: 'Login', query: { redirect: to.fullPath } });
  } else {
    next();
  }
})

export default router;

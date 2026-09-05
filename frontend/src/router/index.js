import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import ClientManager from '../views/ClientManager.vue'
import CommunicationLog from '../views/CommunicationLog.vue'

const routes = [
  { path: '/', name: 'dashboard', component: DashboardView },
  { path: '/clients', name: 'clients', component: ClientManager },
  { path: '/communication-log', name: 'communication-log', component: CommunicationLog },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

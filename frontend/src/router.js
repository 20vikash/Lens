import { createRouter, createWebHistory } from 'vue-router'
import Logs from './pages/Logs.vue'

const routes = [{ path: '/', redirect: '/logs' }, { path: '/logs', name: 'Logs', component: Logs }]

export default createRouter({
	history: createWebHistory(),
	routes,
})

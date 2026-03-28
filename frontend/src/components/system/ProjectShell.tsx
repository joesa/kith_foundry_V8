import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'

function ProjectShell() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: 0.05 }}
      className="h-full"
    >
      <Outlet />
    </motion.div>
  )
}

export default ProjectShell

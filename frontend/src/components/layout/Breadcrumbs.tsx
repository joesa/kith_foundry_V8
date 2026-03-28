import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

export function Breadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  // Skip rendering if we're on the root app route or not enough segments
  if (pathnames.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex items-center space-x-2 text-micro uppercase tracking-widest font-bold text-tertiary">
        <li>
          <Link to="/app/home" className="hover:text-secondary transition-colors inline-flex items-center">
             <span className="material-symbols-outlined text-[14px]">home</span>
          </Link>
        </li>
        {pathnames.map((value, index) => {
          // Skip the 'app' base route in breadcrumbs
          if (value === 'app') return null;

          const to = `/${pathnames.slice(0, index + 1).join('/')}`;
          const isLast = index === pathnames.length - 1;
          
          // Clean up UUIDs for display if they look like prj_xxx
          let label = value.replace(/-/g, ' ');
          if (label.startsWith('prj_')) {
            label = 'Project ' + label.substring(4, 12);
          }

          return (
            <motion.li 
              key={to}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-2"
            >
              <span className="material-symbols-outlined text-[14px] opacity-40">chevron_right</span>
              {isLast ? (
                <span className="text-on-surface" aria-current="page">
                  {label}
                </span>
              ) : (
                <Link to={to} className="hover:text-secondary transition-colors">
                  {label}
                </Link>
              )}
            </motion.li>
          );
        })}
      </ol>
    </nav>
  );
}

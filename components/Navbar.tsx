"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { CURRENT_GOALS } from "@/lib/goals";

const links = [
  { href: "/", label: "Accueil" },
  { href: "/stats", label: "Statistiques" },
  { href: "/about", label: "À propos" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0A]/80 backdrop-blur-xl border-b border-white/5"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <span
            className="text-lg sm:text-xl font-extrabold tracking-tight"
            style={{
              fontFamily: "var(--font-display)",
              background: "linear-gradient(135deg, #F0D060, #D4AF37)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            TO1000
          </span>
          <span className="text-[10px] sm:text-xs bg-gold/20 text-gold px-2 py-0.5 rounded-full font-medium">
            {CURRENT_GOALS}
          </span>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`
                  relative px-3 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors
                  ${isActive ? "text-gold" : "text-white/50 hover:text-white/80"}
                `}
              >
                {link.label}
                {isActive && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute inset-0 bg-gold/10 rounded-lg border border-gold/20"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </motion.nav>
  );
}

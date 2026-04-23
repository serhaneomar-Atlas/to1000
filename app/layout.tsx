import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: {
    default: "To1000.com | Compte à rebours vers le 1000e but de Cristiano Ronaldo",
    template: "%s | To1000.com",
  },
  description:
    "Suivez en temps réel le compte à rebours vers le 1000e but de Cristiano Ronaldo. Statistiques, timeline et estimation — combien de temps avant l'histoire ?",
  keywords: [
    "Cristiano Ronaldo",
    "1000 buts",
    "CR7",
    "compte à rebours",
    "goals",
    "football",
    "record",
    "Al Nassr",
    "Portugal",
  ],
  authors: [{ name: "To1000.com" }],
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: "https://to1000.com",
    siteName: "To1000.com",
    title: "Le compte à rebours vers le 1000e but de CR7",
    description:
      "967 buts et ça continue. Suivez en temps réel le chemin de Cristiano Ronaldo vers les 1000 buts.",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "To1000.com — Compte à rebours 1000e but CR7",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Le 1000e but de CR7 arrive — To1000.com",
    description: "Plus que 33 buts. Suivez le compte à rebours en temps réel.",
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
  },
  metadataBase: new URL("https://to1000.com"),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="h-full antialiased scroll-smooth">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-full flex flex-col bg-[#0A0A0A] text-white">
        <Navbar />
        <main className="flex-1 pt-14 sm:pt-16">{children}</main>
        <Footer />
      </body>
    </html>
  );
}

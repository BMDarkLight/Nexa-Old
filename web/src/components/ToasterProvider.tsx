"use client";

import { Toaster } from "sonner";
import React, { useEffect, useState } from "react";

export default function ToastProvider() {
  const [position, setPosition] = useState<"top-center" | "bottom-left">("bottom-left");

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setPosition("top-center");
      } else {
        setPosition("bottom-left");
      }
    };

    handleResize(); 
    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <Toaster
      position={position}
      toastOptions={{
        style: {
          direction: "rtl",
          fontFamily: "inherit",
        },
      }}
    />
  );
}

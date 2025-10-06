import React from "react";
import LoginStructure from "../(login)/components/LoginStructure";

export default function RootSignup({children,}: Readonly<{ children: React.ReactNode; }>) {
    return (
        <LoginStructure>
            {children}
        </LoginStructure>
    );
}

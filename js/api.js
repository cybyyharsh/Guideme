/**
 * Global API Service
 */
window.API = {
    BASE_URL: (() => {
        if (location.hostname.includes("github.io")) return null;
        if (location.hostname === "localhost" || location.hostname === "127.0.0.1") return "http://127.0.0.1:5000";
        return "https://guideme-api.onrender.com";
    })(),


    async request(endpoint, method = "POST", body = null) {
        if (!this.BASE_URL) {
            console.warn("🌐 API disabled (Frontend-only mode)");
            return null;
        }

        try {
            const options = {
                method,
                headers: { "Content-Type": "application/json" }
            };
            if (body) options.body = JSON.stringify(body);

            const url = `${this.BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
            const res = await fetch(url, options);

            if (!res.ok) return null;
            return await res.json();
        } catch (err) {
            console.error("🌐 API Request Failed:", err);
            return null;
        }
    },


    sendChatMessage(message, context = {}) {
        return this.request("/chat/", "POST", { message, ...context });
    },

    createGuestSession() {
        return this.request("/auth/guest");
    },

    signup(data) {
        return this.request("/auth/signup", "POST", data);
    },

    login(data) {
        return this.request("/auth/login", "POST", data);
    }
};

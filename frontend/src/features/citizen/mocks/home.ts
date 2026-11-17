// Données fictives de démonstration. Une absence de demande est représentée par null.
export type CitizenHomeData = {
  firstName: string;
  pendingRequest: null | {
    id: string;
    organization: string;
    purpose: string;
    checks: string[];
    duration: string;
  };
  consultations: {
    id: string;
    date: string;
    dateTime: string;
    time: string;
    organization: string;
    information: string;
    purpose: string;
    source: string;
    basis: string;
  }[];
};

export const citizenHomeDemo: CitizenHomeData = {
  firstName: "Awa",
  pendingRequest: {
    id: "consent-demo-01",
    organization: "Office national d’identification",
    purpose: "votre carte nationale d’identité",
    checks: ["Confirmer votre identité", "Confirmer votre nationalité burkinabè"],
    duration: "30 jours",
  },
  consultations: [
    {
      id: "consultation-01",
      date: "16 nov. 2026",
      dateTime: "2026-11-16T10:30:00Z",
      time: "10 h 30",
      organization: "Direction des transports",
      information: "Votre statut de majorité",
      purpose: "Demande de permis de conduire",
      source: "Registre d’état civil",
      basis: "Votre accord",
    },
    {
      id: "consultation-02",
      date: "14 nov. 2026",
      dateTime: "2026-11-14T09:15:00Z",
      time: "09 h 15",
      organization: "Office national d’identification",
      information: "Votre identité",
      purpose: "Demande de carte nationale d’identité",
      source: "Registre d’état civil",
      basis: "Votre accord",
    },
    {
      id: "consultation-03",
      date: "14 nov. 2026",
      dateTime: "2026-11-14T09:12:00Z",
      time: "09 h 12",
      organization: "Office national d’identification",
      information: "Votre nationalité",
      purpose: "Demande de carte nationale d’identité",
      source: "Registre de nationalité",
      basis: "Votre accord",
    },
  ],
};

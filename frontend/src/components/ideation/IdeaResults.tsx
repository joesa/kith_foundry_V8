// IdeaResults is handled by DiscoverIdeaPage's results phase.
// This file exists as a route target that redirects to the discovery flow.
import { Navigate } from "react-router-dom";

export default function IdeaResults() {
    // The results are shown inline in DiscoverIdeaPage. 
    // If someone navigates here directly, redirect to discover flow.
    return <Navigate to="/ideation/discover" replace />;
}

namespace comp1110_backend;

public class Config
{
    public static readonly int MaximumDepth = 2000;
    public static readonly int MaximumRecursiveRoutes = 4;
    public static readonly int DijkstraRouteCount = 10;
    public static readonly int DijkstraCandidateMultiplier = 20;
    public static readonly int DijkstraExpansionFactor = 16;
    public static readonly double DijkstraDiversityPenaltyWeight = 14.0;
    public static readonly double DijkstraMaxAllowedOverlapRatio = 0.85;
    public static readonly string NetworkFilePath = "network.json";
}
using System.Text.Json.Serialization;

namespace comp1110_backend.Model.Responses;

[Serializable]
public class PossibleRoutes(List<Route> routes)
{
    [JsonPropertyName("routes")]
    public List<Route> Routes { get; } = routes;
}

[Serializable]
public class Route(List<Segment> segments)
{
    [JsonPropertyName("segments")]
    public List<Segment> Segments { get; } = segments;
}
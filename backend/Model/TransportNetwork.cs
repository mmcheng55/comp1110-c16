using System.Text.Json;
using System.Text.Json.Serialization;
using Model;

namespace comp1110_backend.Model
{
    [Serializable]
    public class TransportNetwork(Stop[] allStops, Segment[] allSegments)
    {
        [JsonPropertyName("stops")]
        public Stop[] AllStops { get; } = allStops;

        [JsonPropertyName("segments")]
        public Segment[] AllSegments { get; } = allSegments;

        public string GetSerializedString()
        {
            return JsonSerializer.Serialize(this);
        }
    }
}


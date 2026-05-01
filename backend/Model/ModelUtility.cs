using System.Text.Json;
using Model;

namespace comp1110_backend.Model
{
    public static class ModelUtility
    {
            // Finds all segments that touch the given stop.
        public static bool TryFindAdjacentSegmentsOfStop(TransportNetwork transportNetwork, Stop stopToQuery, out Segment[] adjacentSegmentsOfPoint)
        {
            var stops = transportNetwork.AllStops;
            var segments = transportNetwork.AllSegments;

            List<Segment> resultList = [];
            if (stops.Any(stop => stop == stopToQuery))
            {
                resultList.AddRange(segments.Where(segment => IsStopInSegment(segment, stopToQuery)));
                
                adjacentSegmentsOfPoint = resultList.ToArray();
                return true;
            }

            adjacentSegmentsOfPoint = [];
            return false;
        }

        // Checks whether the stop is one of the segment endpoints.
        public static bool IsStopInSegment(Segment segment, Stop stop)
        {
            return stop == segment.FromStop || stop == segment.ToStop;
        }

        // Deserializes a full transport network JSON payload.
        public static TransportNetwork? DeserializeTransportNetwork(string rawString)
        {
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
            var networkClass = JsonSerializer.Deserialize<TransportNetwork>(rawString, options);

            return networkClass;
        }

        // Deserializes a single stop JSON payload.
        public static Stop? DeserializeStopClass(string rawString)
        {
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
            var stop = JsonSerializer.Deserialize<Stop>(rawString, options);

            return stop;
        }

        // Serializes the list of route options back to JSON.
        public static string SerializeAllOptions(List<List<Segment>> allOptions)
        {
            return JsonSerializer.Serialize(allOptions);
        }
    }
}
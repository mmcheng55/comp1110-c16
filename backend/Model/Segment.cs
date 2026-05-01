using System.Text.Json.Serialization;
using Model;

namespace comp1110_backend.Model
{
    /// <summary>
    /// Note that order of stops does NOT matter with a segment. <br></br>
    /// <see cref="Segment"/> are undirected even if internally it is defined by a "from to" direction.
    /// </summary>
    [Serializable]
    public class Segment(Stop fromStop, Stop toStop, string segmentTransportationType, string? line, float fareDollars, int timeMin, int scenicIndex)
        : IEquatable<Segment>
    {
        [JsonPropertyName("from")]
        public Stop FromStop { get; } = fromStop;

        [JsonPropertyName("to")]
        public Stop ToStop { get; } = toStop;
        
        [JsonPropertyName("type")]
        public string SegmentTransportationType { get; } = segmentTransportationType;

        [JsonPropertyName("line")]
        public string? Line { get; } = line;

        [JsonPropertyName("fare")]
        public float FareDollars { get; } = fareDollars;

        [JsonPropertyName("time")]
        public int TimeMin { get; } = timeMin;

        [JsonPropertyName("scenic")]
        public int ScenicIndex { get; } = scenicIndex;

        public bool Equals(Segment? other)
        {
            if (other is null) return false;
            if (ReferenceEquals(this, other)) return true;
            return FromStop.Equals(other.FromStop) && 
                   ToStop.Equals(other.ToStop) && 
                   SegmentTransportationType.Equals(other.SegmentTransportationType) && 
                   Line == other.Line &&
                   FareDollars.Equals(other.FareDollars) &&
                   TimeMin.Equals(other.TimeMin) &&
                   ScenicIndex.Equals(other.ScenicIndex);
        }

        public override bool Equals(object? obj)
        {
            if (obj is null) return false;
            if (ReferenceEquals(this, obj)) return true;
            if (obj.GetType() != GetType()) return false;
            return Equals((Segment)obj);
        }

        public override int GetHashCode()
        {
            return HashCode.Combine(FromStop, ToStop, SegmentTransportationType, Line);
        }
    }
}
using comp1110_backend;
using comp1110_backend.Model;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using System.IO;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddMemoryCache();
var app = builder.Build();

View view = new View(app.Services.GetRequiredService<Microsoft.Extensions.Caching.Memory.IMemoryCache>());

if (File.Exists(Config.NetworkFilePath))
{
    var networkString = File.ReadAllText(Config.NetworkFilePath);
    var network = ModelUtility.DeserializeTransportNetwork(networkString);
    if (network != null)
    {
        view.LoadInitialNetwork(network);
        Console.WriteLine("Loaded initial transport network from file.");
    }
}

app.MapGet("/", View.Debug);
app.MapGet("/route", view.GetRoute);

app.MapGet("/network", view.GetNetwork);
app.MapPost("/network/set", view.SetNetwork);
// app.MapPost("/network/nodes", View.HTTP_SetNetwork);
// app.MapPost("/network/set", View.HTTP_SetNetwork);  // TODO: this should be post, but for testing purposes we can use get and query string
app.Run();

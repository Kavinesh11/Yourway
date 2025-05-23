import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access API keys securely
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
AQICN_API_KEY = os.getenv("AQICN_API_KEY")
OSRM_URL = os.getenv("OSRM_SERVER_URL")

# Ensure project root is in sys.path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from fedex_route_optimizer.route_engine.route_optimizer import RouteOptimizer
    from fedex_route_optimizer.config import settings
    from fedex_route_optimizer.emissions.emissions_calculator import EmissionsCalculator
    from fedex_route_optimizer.utils.data_validator import DataValidator
    from fedex_route_optimizer.utils.geocoding import GeocodingService
    from fedex_route_optimizer.utils.logger_setup import setup_logger
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback imports for when modules don't exist
    try:
        from route_engine.route_optimizer import RouteOptimizer
        print("✓ Successfully imported RouteOptimizer")
    except ImportError:
        print("✗ Failed to import RouteOptimizer")
        RouteOptimizer = None
    
    def setup_logger(name):
        import logging
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

class InterfaceManager:
    def __init__(self, root):
        self.root = root
        self.logger = setup_logger("UI_Interface")
        
        # Initialize API clients with environment variables
        self.api_clients = {
            'tomtom_api_key': TOMTOM_API_KEY,
            'google_api_key': GOOGLE_API_KEY,
            'aqicn_api_key': AQICN_API_KEY,
            'osrm_url': OSRM_URL
        }
        
        # Check if API keys are loaded
        self._check_api_keys()
        
        # Initialize RouteOptimizer - ONLY ONCE!
        if RouteOptimizer:
            self.route_optimizer = RouteOptimizer(api_clients=self.api_clients)
            
            # Verify the method exists
            if hasattr(self.route_optimizer, 'calculate_routes'):
                self.logger.info("✓ RouteOptimizer initialized successfully with calculate_routes method")
            else:
                self.logger.error("✗ RouteOptimizer missing calculate_routes method")
                messagebox.showerror("Initialization Error", "RouteOptimizer is missing the calculate_routes method")
        else:
            self.route_optimizer = None
            messagebox.showerror("Initialization Error", "Failed to import RouteOptimizer")
        
        # Initialize other components
        self.emissions_calculator = EmissionsCalculator(settings=settings)
        self.data_validator = DataValidator()
        self.geocoding_service = GeocodingService()

        self.setup_ui()
        self.root.title("FedEx Route Optimizer")
        self.root.geometry("800x600")

        self.settings_tab = ttk.Frame(self.root)
        self.settings_tab.pack(fill=tk.BOTH, expand=True)

        self._setup_settings_tab()

    
    def _check_api_keys(self):
        """Check if API keys are properly loaded from environment variables."""
        missing_keys = []
        
        if not TOMTOM_API_KEY:
            missing_keys.append("TOMTOM_API_KEY")
        if not GOOGLE_API_KEY:
            missing_keys.append("GOOGLE_MAPS_API_KEY")
        if not AQICN_API_KEY:
            missing_keys.append("AQICN_API_KEY")
        if not OSRM_URL:
            missing_keys.append("OSRM_SERVER_URL")
        
        if missing_keys:
            warning_msg = f"Missing environment variables: {', '.join(missing_keys)}\n"
            warning_msg += "Please ensure your .env file contains all required API keys."
            self.logger.warning(warning_msg)
        else:
            self.logger.info("✓ All API keys loaded successfully from environment variables")

    def setup_ui(self):
        """Setup the main application UI."""
        self.root.title("FedEx Route Optimizer")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.route_tab = ttk.Frame(self.notebook)
        self.emissions_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.route_tab, text="Route Optimization")
        self.notebook.add(self.emissions_tab, text="Emissions Analysis")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Set up each tab's content
        self._setup_route_tab()
        self._setup_emissions_tab()
        self._setup_settings_tab()
        
        # Status bar at the bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_route_tab(self):
        """Setup the route optimization tab."""
        # Create frames for input and results sections
        input_frame = ttk.LabelFrame(self.route_tab, text="Route Inputs")
        input_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        results_frame = ttk.LabelFrame(self.route_tab, text="Route Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input fields for origin
        ttk.Label(input_frame, text="Origin:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.origin_var = tk.StringVar()
        self.origin_var.set("")  # Default value for testing
        ttk.Entry(input_frame, textvariable=self.origin_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        
        # Input fields for destination
        ttk.Label(input_frame, text="Destination:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.destination_var = tk.StringVar()
        self.destination_var.set("")  # Default value for testing
        ttk.Entry(input_frame, textvariable=self.destination_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        
        # Vehicle type dropdown
        ttk.Label(input_frame, text="Vehicle Type:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.vehicle_type_var = tk.StringVar()
        vehicle_types = ["delivery_van", "cargo_truck", "electric_van", "box_truck"]
        ttk.Combobox(input_frame, textvariable=self.vehicle_type_var, values=vehicle_types, state="readonly").grid(
            row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.vehicle_type_var.set(vehicle_types[0])
        
        # Optimization criteria
        ttk.Label(input_frame, text="Optimization Priority:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.optimization_var = tk.StringVar()
        optimization_options = ["balanced", "time", "emissions"]
        ttk.Combobox(input_frame, textvariable=self.optimization_var, values=optimization_options, state="readonly").grid(
            row=3, column=1, padx=5, pady=5, sticky=tk.W)
        self.optimization_var.set(optimization_options[0])
        
        # Button to calculate routes
        self.calculate_button = ttk.Button(input_frame, text="Calculate Routes", command=self._calculate_routes)
        self.calculate_button.grid(row=4, column=1, padx=5, pady=10, sticky=tk.E)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(input_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=4, column=0, padx=5, pady=10, sticky=tk.EW)
        
        # Results section using a Treeview for route options
        self.routes_tree = ttk.Treeview(results_frame, columns=("time", "distance", "emissions", "score"), show="headings")
        self.routes_tree.heading("time", text="Time")
        self.routes_tree.heading("distance", text="Distance")
        self.routes_tree.heading("emissions", text="Emissions")
        self.routes_tree.heading("score", text="Score")
        
        self.routes_tree.column("time", width=100)
        self.routes_tree.column("distance", width=100)
        self.routes_tree.column("emissions", width=100)
        self.routes_tree.column("score", width=80)
        
        self.routes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for the treeview
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.routes_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.routes_tree.configure(yscrollcommand=scrollbar.set)
        
        # Route details section
        details_frame = ttk.LabelFrame(self.route_tab, text="Route Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.route_details = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, width=40, height=10)
        self.route_details.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind select event for route details
        self.routes_tree.bind("<<TreeviewSelect>>", self._show_route_details)
    
    def _setup_emissions_tab(self):
        """Setup the emissions analysis tab."""
        # Input section
        input_frame = ttk.LabelFrame(self.emissions_tab, text="Vehicle Information")
        input_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        # Vehicle fields
        ttk.Label(input_frame, text="Make:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.vehicle_make_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.vehicle_make_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.vehicle_model_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.vehicle_model_var).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Year:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.vehicle_year_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.vehicle_year_var).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Fuel Type:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.fuel_type_var = tk.StringVar()
        fuel_types = ["Gasoline", "Diesel", "Electric", "Hybrid", "Natural Gas"]
        ttk.Combobox(input_frame, textvariable=self.fuel_type_var, values=fuel_types, state="readonly").grid(
            row=3, column=1, padx=5, pady=5)
        self.fuel_type_var.set(fuel_types[0])
        
        # Analyze button
        ttk.Button(input_frame, text="Calculate Emissions", command=self._calculate_emissions).grid(
            row=4, column=1, padx=5, pady=10, sticky=tk.E)
        
        # Results section
        results_frame = ttk.LabelFrame(self.emissions_tab, text="Emissions Analysis")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.emissions_results = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.emissions_results.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _setup_settings_tab(self):
        """Setup the settings tab for configuration."""
        # API Status section
    
    def _calculate_routes(self):
        """Calculate routes based on user inputs."""
        if not self.route_optimizer:
            messagebox.showerror("Error", "RouteOptimizer not initialized")
            return
            
        try:
            # Validate inputs
            origin = self.origin_var.get().strip()
            destination = self.destination_var.get().strip()
            vehicle_type = self.vehicle_type_var.get()
            optimization = self.optimization_var.get()
            
            if not self.data_validator.validate_location(origin):
                messagebox.showerror("Input Error", "Invalid origin address")
                return
                
            if not self.data_validator.validate_location(destination):
                messagebox.showerror("Input Error", "Invalid destination address")
                return
            
            # Update status
            self.status_var.set("Calculating routes...")
            self.progress_var.set(10)
            self.root.update()
            
            # Disable the calculate button to prevent multiple clicks
            self.calculate_button.config(state='disabled')
            
            # Run route calculation in a separate thread to prevent UI freezing
            threading.Thread(target=self._run_route_calculation, 
                            args=(origin, destination, vehicle_type, optimization)).start()
            
        except Exception as e:
            self.logger.error(f"Error calculating routes: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_var.set("Error occurred")
            self.calculate_button.config(state='normal')
    
    def _run_route_calculation(self, origin, destination, vehicle_type, optimization):
        """Run the route calculation in a separate thread."""
        try:
            self.logger.info(f"Calling calculate_routes with: origin={origin}, destination={destination}, vehicle_type={vehicle_type}, optimization={optimization}")
            
            # Call the route optimizer with STRING addresses (not coordinates)
            result = self.route_optimizer.calculate_routes(
                origin=origin,
                destination=destination,
                vehicle_type=vehicle_type,
                optimization_priority=optimization
            )
            
            self.logger.info(f"Route calculation result status: {result.get('status')}")
            
            # Update the progress bar
            self.progress_var.set(80)
            
            if result.get('status') == 'success':
                routes = result.get('routes', [])
                self.logger.info(f"Found {len(routes)} routes")
                
                # Update UI with results
                self.root.after(0, lambda: self._update_routes_ui(routes, result))
            else:
                error_msg = result.get('message', 'Unknown error')
                self.logger.error(f"Route calculation failed: {error_msg}")
                self.root.after(0, lambda: messagebox.showerror("Route Calculation Error", error_msg))
                self.root.after(0, lambda: self._reset_ui())
            
        except Exception as e:
            error_msg = f"Error in route calculation thread: {str(e)}"
            self.logger.error(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self._reset_ui())
    
    def _update_routes_ui(self, routes, result):
        """Update the UI with route calculation results."""
        try:
            # Clear previous results
            for item in self.routes_tree.get_children():
                self.routes_tree.delete(item)
            
            # Add new routes
            for i, route in enumerate(routes):
                # Convert seconds to minutes for display
                duration_min = route.get('duration_seconds', 0) // 60
                # Convert meters to miles/km for display
                distance_km = route.get('distance_meters', 0) / 1000
                emissions = route.get('emissions_kg_co2', 0)
                score = route.get('score', 0)
                
                self.routes_tree.insert("", "end", iid=str(i), values=(
                    f"{duration_min} min",
                    f"{distance_km:.1f} km",
                    f"{emissions:.2f} kg CO2",
                    f"{score}/100"
                ))
            
            # Complete the progress
            self.progress_var.set(100)
            self.status_var.set(f"Found {len(routes)} routes")
            
            # Select the first route by default
            if routes:
                self.routes_tree.selection_set("0")
                self._show_route_details(None)
                
            # Re-enable the calculate button
            self.calculate_button.config(state='normal')
            
        except Exception as e:
            self.logger.error(f"Error updating routes UI: {str(e)}")
            self._reset_ui()
    
    def _reset_ui(self):
        """Reset UI to ready state."""
        self.progress_var.set(0)
        self.status_var.set("Ready")
        self.calculate_button.config(state='normal')
    
    def _show_route_details(self, event):
        """Show details for the selected route."""
        selected_items = self.routes_tree.selection()
        if not selected_items:
            return
            
        try:
            route_idx = int(selected_items[0])
            
            # Clear previous details
            self.route_details.delete(1.0, tk.END)
            
            # Show basic route information
            details_text = f"Route {route_idx + 1} Details\n"
            details_text += "=" * 30 + "\n\n"
            
            # Get route values from the tree
            item = self.routes_tree.item(selected_items[0])
            values = item['values']
            
            if values:
                details_text += f"Duration: {values[0]}\n"
                details_text += f"Distance: {values[1]}\n"
                details_text += f"Emissions: {values[2]}\n"
                details_text += f"Score: {values[3]}\n\n"
            
            details_text += "Route Information:\n"
            details_text += "- Traffic conditions considered\n"
            details_text += "- Weather data integrated\n"
            details_text += "- Emissions calculated\n"
            details_text += "- Multi-provider route comparison\n\n"
            
            details_text += "This route has been optimized based on your selected criteria.\n"
            details_text += "Detailed turn-by-turn directions would be available with full API integration."
            
            self.route_details.insert(tk.END, details_text)
            
        except Exception as e:
            self.logger.error(f"Error showing route details: {str(e)}")
    
    def _calculate_emissions(self):
        """Calculate emissions for the vehicle specified in the emissions tab."""
        try:
            make = self.vehicle_make_var.get().strip()
            model = self.vehicle_model_var.get().strip()
            year = self.vehicle_year_var.get().strip()
            fuel_type = self.fuel_type_var.get()
            
            # Input validation
            if not make or not model:
                messagebox.showerror("Input Error", "Please enter vehicle make and model")
                return
                
            if not year.isdigit() or int(year) < 1900 or int(year) > 2100:
                messagebox.showerror("Input Error", "Please enter a valid year")
                return
            
            # Update status
            self.status_var.set("Calculating emissions...")
            
            # Get baseline emissions
            baseline_emissions = self.emissions_calculator.get_vehicle_baseline_emissions(fuel_type)
            
            # Generate report
            report = f"Emissions Analysis for {year} {make} {model}\n"
            report += "=" * 50 + "\n"
            report += f"Fuel Type: {fuel_type}\n\n"
            report += f"Baseline CO2 Emissions: {baseline_emissions:.2f} g/km\n\n"
            
            if fuel_type == "Gasoline":
                report += "Typical Efficiency: 20-30 MPG\n"
                report += "Annual CO2 for 15,000 miles: ~5-7 metric tons\n"
            elif fuel_type == "Diesel":
                report += "Typical Efficiency: 25-35 MPG\n"
                report += "Annual CO2 for 15,000 miles: ~4-6 metric tons\n"
            elif fuel_type == "Electric":
                report += "Zero direct emissions\n"
                report += "Indirect emissions depend on electricity source\n"
            elif fuel_type == "Hybrid":
                report += "Typical Efficiency: 40-50 MPG\n"
                report += "Annual CO2 for 15,000 miles: ~3-4 metric tons\n"
            
            report += "\nRecommendations:\n"
            report += "1. Regular maintenance to optimize fuel efficiency\n"
            report += "2. Eco-driving techniques can reduce emissions by 5-10%\n"
            report += "3. Consider route optimization for further reductions\n"
            report += "4. Plan trips to minimize empty miles\n"
            
            # Update UI
            self.emissions_results.delete(1.0, tk.END)
            self.emissions_results.insert(tk.END, report)
            
            self.status_var.set("Emissions calculation complete")
            
        except Exception as e:
            self.logger.error(f"Error calculating emissions: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_var.set("Error occurred")
            
    def save_settings(self):
        """Save only general settings to config file (not API keys)."""
        try:
            import json

            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
            os.makedirs(config_dir, exist_ok=True)

            config_file = os.path.join(config_dir, "general_settings.json")

            settings = {
                "general": {
                    "units": self.units_var.get(),
                    "log_level": self.log_level_var.get()
                }
            }

            with open(config_file, "w") as f:
                json.dump(settings, f, indent=4)

            messagebox.showinfo("Settings", "Settings saved successfully")

        except Exception as e:
            self.logger.error(f"Error saving general settings: {str(e)}")
            messagebox.showerror("Error", f"Error saving general settings: {str(e)}")
    def _setup_settings_tab(self):
        general_settings_frame = ttk.LabelFrame(self.settings_tab, text="General Settings")
        general_settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Distance Units Dropdown
        ttk.Label(general_settings_frame, text="Distance Units:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.units_var = tk.StringVar()
        distance_units = ["Miles", "Kilometers"]
        ttk.Combobox(general_settings_frame, textvariable=self.units_var, values=distance_units, state="readonly").grid(row=0, column=1, padx=5, pady=5)
        self.units_var.set(distance_units[0])

        # Log Level Dropdown
        ttk.Label(general_settings_frame, text="Log Level:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.log_level_var = tk.StringVar()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ttk.Combobox(general_settings_frame, textvariable=self.log_level_var, values=log_levels, state="readonly").grid(row=1, column=1, padx=5, pady=5)
        self.log_level_var.set(log_levels[1])

        # Save Settings Button
        ttk.Button(general_settings_frame, text="Save General Settings", command=self.save_settings).grid(row=2, column=1, padx=5, pady=10, sticky=tk.E)

        self._load_settings()        

    def _load_settings(self):
        """Load only general settings from config file."""
        try:
            import json

            config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "general_settings.json"
            )

            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    settings = json.load(f)

                # Load general settings
                general = settings.get("general", {})
                if "units" in general:
                    self.units_var.set(general["units"])
                if "log_level" in general:
                    self.log_level_var.set(general["log_level"])

        except Exception as e:
            self.logger.error(f"Error loading general settings: {str(e)}")
            # Don't show error to user, just use defaults




# Remove the old _save_settings and _load_settings methods since they're no longer needed
# The API keys are now loaded from environment variables at the top of the file
if __name__ == "__main__":
    root = tk.Tk()
    app = InterfaceManager(root)
    root.mainloop()